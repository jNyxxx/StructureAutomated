"""Tests for the local/mock-only stability smoke command."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.scripts import local_e2e_smoke, local_stability_smoke
from app.scripts.local_stability_smoke import (
    DEFAULT_TENANT_ID,
    StabilityEnvironmentError,
    StabilityResult,
    StabilityStepError,
    ensure_stability_env_allowed,
    main,
    print_summary,
    run_stability,
)

_TENANT = DEFAULT_TENANT_ID
_OUTBOUND_ID = uuid.uuid4()
_REQUIRED_STEPS = [
    "draft_generate",
    "review_queue",
    "review_approve",
    "send_gate_dry_run",
    "mock_send",
    "outbound_readback",
    "audit_trail",
    "logout_relogin",
]


def test_stability_refuses_non_local_envs() -> None:
    for env in ("staging", "production", "some-unknown-env"):
        with pytest.raises(StabilityEnvironmentError):
            ensure_stability_env_allowed(Settings(app_env=env))


def test_stability_allows_local_mock_envs() -> None:
    for env in ("local", "development", "demo"):
        ensure_stability_env_allowed(Settings(app_env=env))


def test_stability_main_returns_nonzero_on_failed_step(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fail_run(**kwargs: Any) -> StabilityResult:
        raise StabilityStepError("health_readiness", "simulated failure")

    monkeypatch.setattr(local_stability_smoke, "run", _fail_run)

    assert main([]) == 1


def test_stability_summary_includes_pass_fail_counts(capsys: pytest.CaptureFixture[str]) -> None:
    result = StabilityResult(
        tenant_id=_TENANT,
        health_iterations=1,
        auth_cycles=1,
        parallel_auth_sessions=1,
        e2e_repeats=1,
        readback_iterations=1,
        request_count=12,
        server_500_count=0,
        clean_failure_count=2,
        e2e_run_count=2,
        pass_count=9,
    )

    print_summary(result)

    out = capsys.readouterr().out
    assert "STABILITY PASSED" in out
    assert "passes=9" in out
    assert "failures=0" in out
    assert "server_500s=0" in out
    assert "clean_failures=2" in out


def _principal_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "principal": {
                "provider_user_id": "local_mock_user",
                "user_id": "11111111-1111-1111-1111-111111111111",
                "email": "owner@example.com",
                "tenant_id": str(_TENANT),
                "role": "owner",
                "membership_version": 1,
                "mfa_verified": True,
            }
        },
    )


def _revoked_response() -> httpx.Response:
    return httpx.Response(
        401,
        json={
            "error": {
                "code": "AUTH_SESSION_REVOKED",
                "message": "Authentication required.",
                "details": {},
                "request_id": None,
            }
        },
    )


def _error_response(status_code: int, code: str) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "error": {
                "code": code,
                "message": "Expected local smoke error.",
                "details": {},
                "request_id": None,
            }
        },
    )


def _build_handler(*, health_status: int = 200, outbound_status: str = "mock_sent"):
    revoked_tokens: set[str] = set()

    def handler(request: httpx.Request) -> httpx.Response:
        method = request.method
        path = request.url.path
        token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        tenant = request.headers.get("x-tenant-id")

        if method == "GET" and path == "/health":
            return httpx.Response(health_status, json={"status": "ok"})
        if method == "GET" and path == "/live":
            return httpx.Response(200, json={"status": "alive", "service": "backend"})
        if method == "GET" and path == "/ready":
            return httpx.Response(200, json={"status": "ok", "checks": {"database": "ok"}})

        if method == "GET" and path == "/auth/me":
            if not tenant:
                return _error_response(400, "TENANT_REQUIRED")
            if token.startswith("invalid-local-stability-token"):
                return _error_response(401, "UNAUTHENTICATED")
            if token in revoked_tokens:
                return _revoked_response()
            return _principal_response()

        if method == "POST" and path == "/auth/logout":
            revoked_tokens.add(token)
            return httpx.Response(200, json={"revoked": 1})

        if method == "GET" and path == "/api/v1/outbound-messages":
            return httpx.Response(
                200,
                json={
                    "outbound_messages": [
                        {
                            "id": str(_OUTBOUND_ID),
                            "draft_id": str(uuid.uuid4()),
                            "status": outbound_status,
                        }
                    ],
                    "page": {"next_cursor": None, "limit": 100},
                },
            )

        if method == "GET" and path == "/api/v1/audit-events":
            return httpx.Response(
                200,
                json={
                    "audit_events": [{"id": str(uuid.uuid4()), "event_type": "draft.generated"}],
                    "page": {"next_cursor": None, "limit": 25},
                },
            )

        raise AssertionError(f"unexpected request in mock transport: {method} {path}")

    return handler


def _fake_e2e_state(*, steps: list[str] | None = None) -> local_e2e_smoke._SmokeState:
    return local_e2e_smoke._SmokeState(
        tenant_id=_TENANT,
        idempotency_prefix="test-stability",
        passed_steps=steps or list(_REQUIRED_STEPS),
        outbound_message_id=_OUTBOUND_ID,
    )


@pytest.mark.asyncio
async def test_stability_smoke_happy_path_has_summary_and_masks_tokens(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def _fake_run_smoke(*args: Any, **kwargs: Any) -> local_e2e_smoke._SmokeState:
        return _fake_e2e_state()

    monkeypatch.setattr(local_e2e_smoke, "run_smoke", _fake_run_smoke)
    transport = httpx.MockTransport(_build_handler())
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        result = await run_stability(
            client,
            tenant_id=_TENANT,
            run_id="secret-run-id",
            health_iterations=1,
            auth_cycles=1,
            parallel_auth_sessions=1,
            e2e_repeats=1,
            readback_iterations=1,
        )
    print_summary(result)

    out = capsys.readouterr().out
    assert "STABILITY PASSED" in out
    assert "token-sentinel:secret-run-id" not in out
    assert "token-sentinel:***" in out
    assert result.server_500_count == 0
    assert result.clean_failure_count == 2
    assert result.e2e_run_count == 2


@pytest.mark.asyncio
async def test_stability_fails_cleanly_on_5xx_health(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_run_smoke(*args: Any, **kwargs: Any) -> local_e2e_smoke._SmokeState:
        return _fake_e2e_state()

    monkeypatch.setattr(local_e2e_smoke, "run_smoke", _fake_run_smoke)
    transport = httpx.MockTransport(_build_handler(health_status=500))
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        with pytest.raises(StabilityStepError) as exc_info:
            await run_stability(
                client,
                tenant_id=_TENANT,
                run_id="failure-run",
                health_iterations=1,
                auth_cycles=0,
                parallel_auth_sessions=0,
                e2e_repeats=0,
                readback_iterations=0,
            )

    assert exc_info.value.step == "health_readiness[1]/health"


@pytest.mark.asyncio
async def test_stability_requires_review_send_and_audit_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_run_smoke(*args: Any, **kwargs: Any) -> local_e2e_smoke._SmokeState:
        return _fake_e2e_state(steps=["draft_generate", "mock_send", "outbound_readback"])

    monkeypatch.setattr(local_e2e_smoke, "run_smoke", _fake_run_smoke)
    transport = httpx.MockTransport(_build_handler())
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        with pytest.raises(StabilityStepError) as exc_info:
            await run_stability(
                client,
                tenant_id=_TENANT,
                run_id="gate-bypass-run",
                health_iterations=0,
                auth_cycles=0,
                parallel_auth_sessions=0,
                e2e_repeats=0,
                readback_iterations=0,
            )

    assert exc_info.value.step == "e2e_required_steps"
    assert "review_approve" in exc_info.value.detail
    assert "send_gate_dry_run" in exc_info.value.detail


@pytest.mark.asyncio
async def test_stability_rejects_non_mock_outbound_status(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_run_smoke(*args: Any, **kwargs: Any) -> local_e2e_smoke._SmokeState:
        return _fake_e2e_state()

    monkeypatch.setattr(local_e2e_smoke, "run_smoke", _fake_run_smoke)
    transport = httpx.MockTransport(_build_handler(outbound_status="sent"))
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        with pytest.raises(StabilityStepError) as exc_info:
            await run_stability(
                client,
                tenant_id=_TENANT,
                run_id="non-mock-run",
                health_iterations=0,
                auth_cycles=0,
                parallel_auth_sessions=0,
                e2e_repeats=0,
                readback_iterations=0,
            )

    assert exc_info.value.step == "mock_outbound_readback"
