"""Tests for the local/mock-only repeatable E2E smoke command (P4-LocalE2E-SmokeScript)."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.scripts import bootstrap_local_demo, seed_local_grounding
from app.scripts.local_e2e_smoke import (
    DEFAULT_TENANT_ID,
    SmokeEnvironmentError,
    SmokeStepError,
    ensure_smoke_env_allowed,
    run_smoke,
)

_TENANT = DEFAULT_TENANT_ID
_USER = bootstrap_local_demo.DEFAULT_USER_ID
_SMOKE_EMAIL = "smoke-e2e@example.com"

_IMPORT_ID = uuid.uuid4()
_CONTACT_ID = uuid.uuid4()
_CAMPAIGN_ID = uuid.uuid4()
_DRAFT_ID = uuid.uuid4()
_REVIEW_ID = uuid.uuid4()
_OUTBOUND_ID = uuid.uuid4()

_RUN_ID = "unittestrun1"
_PRIMARY_TOKEN = f"token-sentinel:{_RUN_ID}"
_RELOGIN_TOKEN = f"token-sentinel:{_RUN_ID}-b"


def test_smoke_refuses_non_local_envs() -> None:
    for env in ("staging", "production", "some-unknown-env"):
        with pytest.raises(SmokeEnvironmentError):
            ensure_smoke_env_allowed(Settings(app_env=env))


def test_smoke_allows_local_mock_envs() -> None:
    for env in ("local", "development", "demo"):
        ensure_smoke_env_allowed(Settings(app_env=env))


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


def _principal_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "principal": {
                "provider_user_id": "local_mock_user",
                "user_id": str(_USER),
                "email": "owner@example.com",
                "tenant_id": str(_TENANT),
                "role": "owner",
                "membership_version": 1,
                "mfa_verified": True,
            }
        },
    )


def _build_handler(
    *,
    draft_status: str = "generated",
    send_mock_only: bool = True,
    send_status: str = "mock_sent",
    replay: bool = False,
):
    """Build a mock transport handler.

    ``replay=True`` simulates every idempotency-gated endpoint hitting a
    prior-completed key: the created-resource field comes back ``None`` with
    ``idempotency_replay: true`` (the real contract — see
    ``app/services/idempotency.py``), and the GET/list lookup endpoints the
    script falls back to are wired up so it can still recover state.
    """
    revoked_token: dict[str, str | None] = {"value": None}

    def handler(request: httpx.Request) -> httpx.Response:
        method = request.method
        path = request.url.path
        token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()

        if method == "GET" and path == "/auth/me":
            if token == revoked_token["value"]:
                return _revoked_response()
            return _principal_response()

        if method == "POST" and path == "/auth/logout":
            revoked_token["value"] = token
            return httpx.Response(200, json={"revoked": 1})

        if method == "POST" and path == "/api/v1/imports/contacts":
            if replay:
                return httpx.Response(201, json={"import": None, "idempotency_replay": True})
            return httpx.Response(
                201,
                json={
                    "import": {
                        "id": str(_IMPORT_ID),
                        "status": "completed",
                        "total_rows": 1,
                        "valid_rows": 1,
                        "invalid_rows": 0,
                        "duplicate_rows": 0,
                    },
                    "idempotency_replay": False,
                },
            )

        if method == "GET" and path == "/api/v1/contacts":
            return httpx.Response(
                200,
                json={
                    "contacts": [
                        {"id": str(_CONTACT_ID), "email": _SMOKE_EMAIL, "full_name": "Smoke E2E"}
                    ],
                    "page": {"next_cursor": None, "limit": 100},
                },
            )

        if method == "POST" and path == "/api/v1/campaigns":
            if replay:
                return httpx.Response(201, json={"campaign": None, "idempotency_replay": True})
            return httpx.Response(
                201,
                json={
                    "campaign": {
                        "id": str(_CAMPAIGN_ID),
                        "name": "Local E2E Smoke Campaign",
                        "status": "draft",
                    },
                    "idempotency_replay": False,
                },
            )

        if method == "GET" and path == "/api/v1/campaigns":
            return httpx.Response(
                200,
                json={
                    "campaigns": [
                        {
                            "id": str(_CAMPAIGN_ID),
                            "name": "Local E2E Smoke Campaign",
                            "status": "draft",
                        }
                    ],
                    "page": {"next_cursor": None, "limit": 100},
                },
            )

        if method == "POST" and path == f"/api/v1/campaigns/{_CAMPAIGN_ID}/contacts":
            if replay:
                return httpx.Response(
                    201, json={"campaign_contact": None, "idempotency_replay": True}
                )
            return httpx.Response(
                201,
                json={
                    "campaign_contact": {
                        "id": str(uuid.uuid4()),
                        "campaign_id": str(_CAMPAIGN_ID),
                        "contact_id": str(_CONTACT_ID),
                        "status": "selected",
                    },
                    "idempotency_replay": False,
                },
            )

        if method == "POST" and path == "/api/v1/drafts/generate":
            if replay:
                return httpx.Response(201, json={"draft": None, "idempotency_replay": True})
            return httpx.Response(
                201,
                json={
                    "draft": {
                        "id": str(_DRAFT_ID),
                        "status": draft_status,
                        "campaign_id": str(_CAMPAIGN_ID),
                        "contact_id": str(_CONTACT_ID),
                    },
                    "idempotency_replay": False,
                },
            )

        if method == "GET" and path == f"/api/v1/drafts/{_DRAFT_ID}":
            return httpx.Response(
                200,
                json={
                    "draft": {
                        "id": str(_DRAFT_ID),
                        "status": draft_status,
                        "campaign_id": str(_CAMPAIGN_ID),
                        "contact_id": str(_CONTACT_ID),
                    }
                },
            )

        if method == "GET" and path == f"/api/v1/drafts/{_DRAFT_ID}/evidence":
            return httpx.Response(200, json={"evidence": [{"id": str(uuid.uuid4())}]})

        if method == "GET" and path == "/api/v1/review/items":
            return httpx.Response(
                200,
                json={
                    "review_items": [
                        {
                            "id": str(_REVIEW_ID),
                            "draft_id": str(_DRAFT_ID),
                            "status": "pending_review",
                        }
                    ],
                    "page": {"next_cursor": None, "limit": 25},
                },
            )

        if method == "GET" and path == f"/api/v1/review/items/{_REVIEW_ID}":
            return httpx.Response(
                200,
                json={
                    "review_item": {
                        "id": str(_REVIEW_ID),
                        "draft_id": str(_DRAFT_ID),
                        "status": "approved",
                    }
                },
            )

        if method == "POST" and path == f"/api/v1/review/items/{_REVIEW_ID}/approve":
            if replay:
                return httpx.Response(200, json={"review_item": None, "idempotency_replay": True})
            return httpx.Response(
                200,
                json={
                    "review_item": {"id": str(_REVIEW_ID), "status": "approved"},
                    "idempotency_replay": False,
                },
            )

        if method == "POST" and path == "/api/v1/send-gate/dry-run":
            if replay:
                return httpx.Response(
                    200,
                    json={
                        "send_gate_result": None,
                        "idempotency_replay": True,
                        "mock_only": True,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "send_gate_result": {
                        "id": str(uuid.uuid4()),
                        "draft_id": str(_DRAFT_ID),
                        "status": "passed",
                    },
                    "idempotency_replay": False,
                    "mock_only": True,
                },
            )

        if method == "POST" and path == "/api/v1/send-intents":
            if replay:
                return httpx.Response(
                    201,
                    json={
                        "result": None,
                        "idempotency_replay": True,
                        "mock_only": send_mock_only,
                    },
                )
            return httpx.Response(
                201,
                json={
                    "result": {
                        "outbound_message_id": str(_OUTBOUND_ID),
                        "status": send_status,
                        "sent_at": "2026-01-01T00:00:00Z",
                    },
                    "idempotency_replay": False,
                    "mock_only": send_mock_only,
                },
            )

        if method == "GET" and path == "/api/v1/outbound-messages":
            return httpx.Response(
                200,
                json={
                    "outbound_messages": [
                        {
                            "id": str(_OUTBOUND_ID),
                            "draft_id": str(_DRAFT_ID),
                            "status": "mock_sent",
                        }
                    ],
                    "page": {"next_cursor": None, "limit": 25},
                },
            )

        if method == "GET" and path == "/api/v1/audit-events":
            events = [
                {"object_id": str(_IMPORT_ID), "event_type": "contact_import.completed"},
                {"object_id": str(_CAMPAIGN_ID), "event_type": "campaign.created"},
                {"object_id": str(_CAMPAIGN_ID), "event_type": "campaign.contact_selected"},
                {"object_id": str(_DRAFT_ID), "event_type": "draft.generated"},
                {"object_id": str(_REVIEW_ID), "event_type": "draft.approved"},
                {"object_id": str(_DRAFT_ID), "event_type": "send_gate.passed"},
                {"object_id": str(_OUTBOUND_ID), "event_type": "outbound_message.sent"},
            ]
            return httpx.Response(
                200, json={"audit_events": events, "page": {"next_cursor": None, "limit": 100}}
            )

        raise AssertionError(f"unexpected request in mock transport: {method} {path}")

    return handler


def _patch_bootstrap_and_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_bootstrap_run(*, tenant_id: uuid.UUID) -> Any:
        return bootstrap_local_demo.BootstrapResult(
            tenant_created=False,
            user_created=False,
            membership_created=False,
            plan_created=False,
            subscription_created=False,
            tenant_id=tenant_id,
            user_id=_USER,
        )

    async def _fake_seed_run(*, tenant_id: uuid.UUID) -> Any:
        return seed_local_grounding.SeedResult(
            created=False,
            document_id=uuid.uuid4(),
            chunk_count=0,
            skipped_reason="already_seeded",
        )

    monkeypatch.setattr(bootstrap_local_demo, "run", _fake_bootstrap_run)
    monkeypatch.setattr(seed_local_grounding, "run", _fake_seed_run)


@pytest.mark.asyncio
async def test_smoke_happy_path_reports_all_steps_passed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_bootstrap_and_seed(monkeypatch)
    transport = httpx.MockTransport(_build_handler())
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        state = await run_smoke(client, tenant_id=_TENANT, run_id=_RUN_ID)

    assert len(state.passed_steps) == 16
    out = capsys.readouterr().out
    for step in state.passed_steps:
        assert f"[PASS] {step}:" in out


@pytest.mark.asyncio
async def test_smoke_happy_path_handles_idempotent_replay_at_every_step(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A second run against the same tenant hits idempotent replay (null
    resource + idempotency_replay=true) at every gated step — this is the
    real contract (app/services/idempotency.py only persists hashes, never
    payloads), so the script must recover state via lookups, not the POST
    response body."""
    _patch_bootstrap_and_seed(monkeypatch)
    transport = httpx.MockTransport(_build_handler(replay=True))
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        state = await run_smoke(client, tenant_id=_TENANT, run_id=_RUN_ID)

    assert len(state.passed_steps) == 16
    assert state.import_id is None
    assert state.campaign_id == _CAMPAIGN_ID
    assert state.draft_id == _DRAFT_ID
    assert state.review_id == _REVIEW_ID
    assert state.outbound_message_id == _OUTBOUND_ID
    out = capsys.readouterr().out
    assert "idempotency_replay=true" in out


@pytest.mark.asyncio
async def test_smoke_reports_failure_cleanly_when_draft_needs_regeneration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bootstrap_and_seed(monkeypatch)
    transport = httpx.MockTransport(_build_handler(draft_status="needs_regeneration"))
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        with pytest.raises(SmokeStepError) as exc_info:
            await run_smoke(client, tenant_id=_TENANT, run_id=_RUN_ID)

    assert exc_info.value.step == "draft_generate"


@pytest.mark.asyncio
async def test_smoke_fails_if_mock_send_is_not_mock_only(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_bootstrap_and_seed(monkeypatch)
    transport = httpx.MockTransport(_build_handler(send_mock_only=False))
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        with pytest.raises(SmokeStepError) as exc_info:
            await run_smoke(client, tenant_id=_TENANT, run_id=_RUN_ID)

    assert exc_info.value.step == "mock_send"


@pytest.mark.asyncio
async def test_smoke_output_does_not_print_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_bootstrap_and_seed(monkeypatch)
    transport = httpx.MockTransport(_build_handler())
    async with httpx.AsyncClient(base_url="http://localhost:8000", transport=transport) as client:
        await run_smoke(client, tenant_id=_TENANT, run_id=_RUN_ID)

    out = capsys.readouterr().out
    assert _PRIMARY_TOKEN not in out
    assert _RELOGIN_TOKEN not in out
    assert "token-sentinel:***" in out
