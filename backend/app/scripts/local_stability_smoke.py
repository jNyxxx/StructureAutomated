"""LOCAL/MOCK-ONLY load and stability smoke for the local Docker backend.

This is not a production load test. It is a modest local stability check meant
to catch obvious auth/session, tenant, idempotency, DB, audit, and mock-send
regressions before demo/client work.

Run from the repo root with the local Docker stack up:

    docker compose exec -T backend python -m app.scripts.local_stability_smoke

The script refuses to run outside ``local``/``development``/``demo``. It uses the
same local/mock auth and HTTP API paths as the app, never bypasses review,
groundedness, send, billing, or tenant gates, and never enables live providers.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.scripts import bootstrap_local_demo, local_e2e_smoke

_ALLOWED_STABILITY_ENVS = frozenset({"local", "development", "demo"})
DEFAULT_BASE_URL = local_e2e_smoke.DEFAULT_BASE_URL
DEFAULT_TENANT_ID = bootstrap_local_demo.DEFAULT_TENANT_ID

DEFAULT_HEALTH_ITERATIONS = 10
DEFAULT_AUTH_CYCLES = 10
DEFAULT_PARALLEL_AUTH_SESSIONS = 5
DEFAULT_E2E_REPEATS = 3
DEFAULT_READBACK_ITERATIONS = 5

_REQUIRED_E2E_STEPS = frozenset(
    {
        "draft_generate",
        "review_queue",
        "review_approve",
        "send_gate_dry_run",
        "mock_send",
        "outbound_readback",
        "audit_trail",
        "logout_relogin",
    }
)


class StabilityEnvironmentError(RuntimeError):
    """Raised when invoked outside an allowed local/mock environment."""


class StabilityStepError(RuntimeError):
    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


@dataclass
class StabilityResult:
    tenant_id: uuid.UUID
    health_iterations: int
    auth_cycles: int
    parallel_auth_sessions: int
    e2e_repeats: int
    readback_iterations: int
    request_count: int = 0
    server_500_count: int = 0
    clean_failure_count: int = 0
    exception_count: int = 0
    e2e_run_count: int = 0
    pass_count: int = 0
    passed_steps: list[str] = field(default_factory=list)

    def record_pass(self, step: str, detail: str) -> None:
        self.pass_count += 1
        self.passed_steps.append(step)
        print(f"[PASS] {step}: {detail}")


def ensure_stability_env_allowed(settings: Settings) -> None:
    if settings.app_env not in _ALLOWED_STABILITY_ENVS:
        raise StabilityEnvironmentError(
            f"Refusing to run local stability smoke: APP_ENV={settings.app_env!r} is not "
            f"one of {sorted(_ALLOWED_STABILITY_ENVS)}. This smoke is local/mock/demo-only."
        )


def _headers(token: str, tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


def _mask(token: str) -> str:
    prefix = token.split(":", 1)[0]
    return f"{prefix}:***"


async def _record_response(result: StabilityResult, response: httpx.Response) -> None:
    result.request_count += 1
    if response.status_code >= 500:
        result.server_500_count += 1


async def _request(
    client: httpx.AsyncClient,
    result: StabilityResult,
    step: str,
    method: str,
    path: str,
    **kwargs: Any,
) -> httpx.Response:
    try:
        response = await client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        result.exception_count += 1
        raise StabilityStepError(step, f"request failed: {exc!r}") from exc
    if response.status_code >= 500:
        raise StabilityStepError(step, f"server error {response.status_code}: {response.text}")
    return response


def _json(response: httpx.Response, step: str) -> dict:
    try:
        body = response.json()
    except ValueError as exc:
        raise StabilityStepError(step, f"non-JSON response: {response.text[:200]!r}") from exc
    if not isinstance(body, dict):
        raise StabilityStepError(step, f"expected JSON object, got {type(body).__name__}")
    return body


async def _run_health_readiness(client: httpx.AsyncClient, result: StabilityResult) -> None:
    endpoints = (
        ("/health", "status", "ok"),
        ("/live", "status", "alive"),
        ("/ready", "status", "ok"),
    )
    for iteration in range(result.health_iterations):
        for path, key, expected in endpoints:
            step = f"health_readiness[{iteration + 1}]{path}"
            response = await _request(client, result, step, "GET", path)
            body = _json(response, step)
            if response.status_code != 200 or body.get(key) != expected:
                raise StabilityStepError(
                    step, f"unexpected response {response.status_code}: {body}"
                )
            result.record_pass(step, f"HTTP 200 {key}={expected}")


async def _run_one_auth_cycle(
    client: httpx.AsyncClient,
    result: StabilityResult,
    *,
    tenant_id: uuid.UUID,
    run_id: str,
    label: str,
) -> None:
    token = f"token-sentinel:{run_id}-{label}"
    relogin_token = f"token-sentinel:{run_id}-{label}-fresh"

    response = await _request(
        client,
        result,
        f"auth_cycle[{label}].login",
        "GET",
        "/auth/me",
        headers=_headers(token, tenant_id),
    )
    body = _json(response, f"auth_cycle[{label}].login")
    principal = body.get("principal", {})
    if response.status_code != 200 or principal.get("tenant_id") != str(tenant_id):
        raise StabilityStepError(f"auth_cycle[{label}].login", f"unexpected principal: {body}")

    response = await _request(
        client,
        result,
        f"auth_cycle[{label}].logout",
        "POST",
        "/auth/logout",
        headers=_headers(token, tenant_id),
    )
    body = _json(response, f"auth_cycle[{label}].logout")
    if response.status_code != 200 or body.get("revoked", 0) < 1:
        raise StabilityStepError(f"auth_cycle[{label}].logout", f"unexpected logout: {body}")

    response = await _request(
        client,
        result,
        f"auth_cycle[{label}].old_rejected",
        "GET",
        "/auth/me",
        headers=_headers(token, tenant_id),
    )
    body = _json(response, f"auth_cycle[{label}].old_rejected")
    if response.status_code != 401 or body.get("error", {}).get("code") != "AUTH_SESSION_REVOKED":
        raise StabilityStepError(
            f"auth_cycle[{label}].old_rejected",
            f"expected AUTH_SESSION_REVOKED, got {response.status_code}: {body}",
        )

    response = await _request(
        client,
        result,
        f"auth_cycle[{label}].relogin",
        "GET",
        "/auth/me",
        headers=_headers(relogin_token, tenant_id),
    )
    body = _json(response, f"auth_cycle[{label}].relogin")
    principal = body.get("principal", {})
    if response.status_code != 200 or principal.get("tenant_id") != str(tenant_id):
        raise StabilityStepError(f"auth_cycle[{label}].relogin", f"unexpected relogin: {body}")

    result.record_pass(
        f"auth_cycle[{label}]",
        f"logout rejected old session and fresh login {_mask(relogin_token)} worked",
    )


async def _run_auth_cycles(
    client: httpx.AsyncClient,
    result: StabilityResult,
    *,
    tenant_id: uuid.UUID,
    run_id: str,
) -> None:
    for index in range(result.auth_cycles):
        await _run_one_auth_cycle(
            client, result, tenant_id=tenant_id, run_id=run_id, label=f"seq-{index + 1}"
        )


async def _run_parallel_auth_probe(
    client: httpx.AsyncClient,
    result: StabilityResult,
    *,
    tenant_id: uuid.UUID,
    run_id: str,
) -> None:
    if result.parallel_auth_sessions <= 0:
        return
    await asyncio.gather(
        *(
            _run_one_auth_cycle(
                client,
                result,
                tenant_id=tenant_id,
                run_id=run_id,
                label=f"parallel-{index + 1}",
            )
            for index in range(result.parallel_auth_sessions)
        )
    )
    result.record_pass(
        "parallel_auth_probe",
        f"{result.parallel_auth_sessions} concurrent local mock sessions completed",
    )


async def _run_clean_failure_checks(
    client: httpx.AsyncClient,
    result: StabilityResult,
    *,
    tenant_id: uuid.UUID,
    run_id: str,
) -> None:
    invalid_token = f"invalid-local-stability-token-{run_id}"
    response = await _request(
        client,
        result,
        "clean_failure.invalid_token",
        "GET",
        "/auth/me",
        headers=_headers(invalid_token, tenant_id),
    )
    body = _json(response, "clean_failure.invalid_token")
    if response.status_code != 401 or body.get("error", {}).get("code") != "UNAUTHENTICATED":
        raise StabilityStepError(
            "clean_failure.invalid_token",
            f"expected UNAUTHENTICATED 401, got {response.status_code}: {body}",
        )
    result.clean_failure_count += 1
    result.record_pass("clean_failure.invalid_token", "401 UNAUTHENTICATED, not 500")

    response = await _request(
        client,
        result,
        "clean_failure.missing_tenant",
        "GET",
        "/auth/me",
        headers={"Authorization": f"Bearer token-sentinel:{run_id}-missing-tenant"},
    )
    body = _json(response, "clean_failure.missing_tenant")
    if response.status_code != 400 or body.get("error", {}).get("code") != "TENANT_REQUIRED":
        raise StabilityStepError(
            "clean_failure.missing_tenant",
            f"expected TENANT_REQUIRED 400, got {response.status_code}: {body}",
        )
    result.clean_failure_count += 1
    result.record_pass("clean_failure.missing_tenant", "400 TENANT_REQUIRED, not 500")


async def _verify_mock_outbound_readback(
    client: httpx.AsyncClient,
    result: StabilityResult,
    *,
    tenant_id: uuid.UUID,
    token: str,
    outbound_message_id: uuid.UUID | None,
    label: str,
) -> None:
    if outbound_message_id is None:
        raise StabilityStepError("mock_outbound_readback", f"{label}: no outbound_message_id")
    response = await _request(
        client,
        result,
        f"mock_outbound_readback[{label}]",
        "GET",
        "/api/v1/outbound-messages",
        headers=_headers(token, tenant_id),
        params={"limit": 100},
    )
    body = _json(response, f"mock_outbound_readback[{label}]")
    matches = [
        message
        for message in body.get("outbound_messages", [])
        if message.get("id") == str(outbound_message_id)
    ]
    if not matches:
        raise StabilityStepError(
            "mock_outbound_readback", f"{label}: outbound message {outbound_message_id} missing"
        )
    status = matches[0].get("status")
    if status != "mock_sent":
        raise StabilityStepError(
            "mock_outbound_readback",
            f"{label}: expected mock_sent outbound status, got {status!r}",
        )
    result.record_pass(
        f"mock_outbound_readback[{label}]", f"outbound_message_id={outbound_message_id} mock_sent"
    )


async def _run_audit_readbacks(
    client: httpx.AsyncClient,
    result: StabilityResult,
    *,
    tenant_id: uuid.UUID,
    token: str,
) -> None:
    for index in range(result.readback_iterations):
        step = f"audit_readback[{index + 1}]"
        response = await _request(
            client,
            result,
            step,
            "GET",
            "/api/v1/audit-events",
            headers=_headers(token, tenant_id),
            params={"limit": 25},
        )
        body = _json(response, step)
        if response.status_code != 200 or not isinstance(body.get("audit_events"), list):
            raise StabilityStepError(
                step, f"unexpected audit response {response.status_code}: {body}"
            )
        result.record_pass(step, f"{len(body.get('audit_events', []))} audit rows readable")


async def _run_e2e_once(
    client: httpx.AsyncClient,
    result: StabilityResult,
    *,
    tenant_id: uuid.UUID,
    run_id: str,
    label: str,
) -> None:
    state = await local_e2e_smoke.run_smoke(client, tenant_id=tenant_id, run_id=f"{run_id}-{label}")
    result.e2e_run_count += 1
    missing_steps = _REQUIRED_E2E_STEPS - set(state.passed_steps)
    if missing_steps:
        raise StabilityStepError(
            "e2e_required_steps", f"{label}: missing required steps {sorted(missing_steps)}"
        )
    verifier_token = f"token-sentinel:{run_id}-{label}-verify"
    await _verify_mock_outbound_readback(
        client,
        result,
        tenant_id=tenant_id,
        token=verifier_token,
        outbound_message_id=state.outbound_message_id,
        label=label,
    )
    await _run_audit_readbacks(client, result, tenant_id=tenant_id, token=verifier_token)
    result.record_pass(
        f"e2e_run[{label}]",
        f"{len(state.passed_steps)} local E2E steps passed with gates exercised",
    )


async def run_stability(
    client: httpx.AsyncClient,
    *,
    tenant_id: uuid.UUID,
    run_id: str,
    health_iterations: int = DEFAULT_HEALTH_ITERATIONS,
    auth_cycles: int = DEFAULT_AUTH_CYCLES,
    parallel_auth_sessions: int = DEFAULT_PARALLEL_AUTH_SESSIONS,
    e2e_repeats: int = DEFAULT_E2E_REPEATS,
    readback_iterations: int = DEFAULT_READBACK_ITERATIONS,
) -> StabilityResult:
    result = StabilityResult(
        tenant_id=tenant_id,
        health_iterations=health_iterations,
        auth_cycles=auth_cycles,
        parallel_auth_sessions=parallel_auth_sessions,
        e2e_repeats=e2e_repeats,
        readback_iterations=readback_iterations,
    )

    async def response_hook(response: httpx.Response) -> None:
        await _record_response(result, response)

    client.event_hooks.setdefault("response", []).append(response_hook)

    result.record_pass(
        "stability_config",
        "health_iterations="
        f"{health_iterations} auth_cycles={auth_cycles} "
        f"parallel_auth_sessions={parallel_auth_sessions} e2e_repeats={e2e_repeats} "
        f"readback_iterations={readback_iterations}",
    )
    await _run_e2e_once(client, result, tenant_id=tenant_id, run_id=run_id, label="precheck")
    await _run_health_readiness(client, result)
    await _run_auth_cycles(client, result, tenant_id=tenant_id, run_id=run_id)
    await _run_parallel_auth_probe(client, result, tenant_id=tenant_id, run_id=run_id)
    await _run_clean_failure_checks(client, result, tenant_id=tenant_id, run_id=run_id)

    for index in range(e2e_repeats):
        await _run_e2e_once(
            client,
            result,
            tenant_id=tenant_id,
            run_id=run_id,
            label=f"repeat-{index + 1}",
        )

    if result.server_500_count:
        raise StabilityStepError(
            "server_500_count", f"observed {result.server_500_count} 5xx responses"
        )

    return result


async def run(
    *,
    base_url: str,
    tenant_id: uuid.UUID,
    health_iterations: int = DEFAULT_HEALTH_ITERATIONS,
    auth_cycles: int = DEFAULT_AUTH_CYCLES,
    parallel_auth_sessions: int = DEFAULT_PARALLEL_AUTH_SESSIONS,
    e2e_repeats: int = DEFAULT_E2E_REPEATS,
    readback_iterations: int = DEFAULT_READBACK_ITERATIONS,
) -> StabilityResult:
    ensure_stability_env_allowed(get_settings())
    run_id = uuid.uuid4().hex[:12]
    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        return await run_stability(
            client,
            tenant_id=tenant_id,
            run_id=run_id,
            health_iterations=health_iterations,
            auth_cycles=auth_cycles,
            parallel_auth_sessions=parallel_auth_sessions,
            e2e_repeats=e2e_repeats,
            readback_iterations=readback_iterations,
        )


def print_summary(result: StabilityResult) -> None:
    print(
        "STABILITY PASSED "
        f"(passes={result.pass_count} failures=0 requests={result.request_count} "
        f"server_500s={result.server_500_count} exceptions={result.exception_count} "
        f"clean_failures={result.clean_failure_count} e2e_runs={result.e2e_run_count})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", type=uuid.UUID, default=DEFAULT_TENANT_ID)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--health-iterations", type=int, default=DEFAULT_HEALTH_ITERATIONS)
    parser.add_argument("--auth-cycles", type=int, default=DEFAULT_AUTH_CYCLES)
    parser.add_argument(
        "--parallel-auth-sessions", type=int, default=DEFAULT_PARALLEL_AUTH_SESSIONS
    )
    parser.add_argument("--e2e-repeats", type=int, default=DEFAULT_E2E_REPEATS)
    parser.add_argument("--readback-iterations", type=int, default=DEFAULT_READBACK_ITERATIONS)
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(
            run(
                base_url=args.base_url,
                tenant_id=args.tenant_id,
                health_iterations=args.health_iterations,
                auth_cycles=args.auth_cycles,
                parallel_auth_sessions=args.parallel_auth_sessions,
                e2e_repeats=args.e2e_repeats,
                readback_iterations=args.readback_iterations,
            )
        )
    except StabilityEnvironmentError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except StabilityStepError as exc:
        print(f"[FAIL] {exc.step}: {exc.detail}", file=sys.stderr)
        print(f"STABILITY FAILED at {exc.step}", file=sys.stderr)
        return 1

    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
