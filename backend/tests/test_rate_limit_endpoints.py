"""Endpoint-level rate-limit regression coverage (P3-4g).

The per-endpoint ``enforce_*`` dependencies live in ``app/ratelimit/dependencies.py``
and protect tenant-scoped routes whose service dependencies open a real
``tenant_session`` (Postgres). The test suite has no test database, so those routes
cannot be exercised end-to-end here. Two complementary layers close that gap:

1. Probe-route behavior tests mount the *real* ``enforce_*`` functions on a minimal
   one-route app backed by a shared ``RateLimitService(InMemoryRateLimitBackend())``
   and prove each one trips 429 at its configured limit and is scoped per tenant.
   Firing ``limit + 1`` requests through one client also proves the counter is shared
   across requests (the original per-request-backend no-op bug stays fixed).
2. A wiring guard introspects ``create_app()`` routes and asserts each real route
   carries its ``enforce_*`` dependency, catching accidental removal.

Not covered here (already tested elsewhere): ``POST /auth/session`` 429 on the real
route (``test_auth.py``), ``DEFAULT_POLICIES``/shared-backend behavior and the
middleware 429/503 envelope (``test_rate_limit.py``). Assertions match the existing
``AppError`` path: status 429 + ``error.code == "RATE_LIMITED"`` (the RateLimit-*/
Retry-After headers are emitted only by the middleware path, not the dependency path).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.main import create_app
from app.middleware.error_handler import register_error_handlers
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.ratelimit.dependencies import (
    enforce_auth_session_rate_limit,
    enforce_campaign_contact_select_rate_limit,
    enforce_campaign_create_rate_limit,
    enforce_followup_rate_limit,
    enforce_import_rate_limit,
    enforce_send_gate_rate_limit,
    enforce_send_intent_rate_limit,
)
from app.services.rate_limit import RateLimitService

TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = uuid.UUID("22222222-2222-2222-2222-222222222222")

# (enforce dependency, its configured per-window limit). The limit values double as a
# check on the configured policy numbers: import=10/5min, risky_action=30/min,
# tenant_send=100/min, tenant_followup=60/min.
CASES: list[tuple[Callable[..., object], int]] = [
    (enforce_import_rate_limit, 10),
    (enforce_campaign_create_rate_limit, 30),
    (enforce_campaign_contact_select_rate_limit, 30),
    (enforce_send_gate_rate_limit, 100),
    (enforce_send_intent_rate_limit, 100),
    (enforce_followup_rate_limit, 60),
]
_CASE_IDS = [dep.__name__ for dep, _ in CASES]


def _principal(tenant_id: uuid.UUID) -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="probe",
        provider_session_ref="probe",
        user_id=uuid.uuid4(),
        email="probe@example.com",
        tenant_id=tenant_id,
        role="owner",
        membership_version=1,
        mfa_verified=True,
    )


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


def _probe_client(dep: Callable[..., object]) -> TestClient:
    """One-route app that mounts the real ``dep`` over a shared rate-limit service.

    ``current_principal`` is overridden to read ``X-Tenant-ID`` so a single app (and
    therefore a single in-memory backend) can serve multiple tenants in one test.
    """
    app = FastAPI()
    app.state.rate_limit_service = RateLimitService(InMemoryRateLimitBackend())
    register_error_handlers(app)

    # NOTE: attach the guard via ``dependencies=[...]``, not a parameter annotation.
    # Under ``from __future__ import annotations`` (PEP 563) a ``Depends(dep)`` written
    # as ``Annotated[None, Depends(dep)]`` is stringified, and FastAPI cannot resolve
    # the closure variable ``dep`` from the module globals -> the dependency silently
    # drops and the route 422s. The decorator argument is evaluated eagerly instead.
    @app.post("/probe", dependencies=[Depends(dep)])
    async def _probe() -> dict[str, bool]:
        return {"ok": True}

    def _override(request: Request) -> CurrentPrincipal:
        return _principal(uuid.UUID(request.headers["X-Tenant-ID"]))

    app.dependency_overrides[current_principal] = _override
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(("dep", "limit"), CASES, ids=_CASE_IDS)
def test_enforce_blocks_after_limit(dep: Callable[..., object], limit: int) -> None:
    client = _probe_client(dep)
    headers = _headers(TENANT_A)

    allowed = [client.post("/probe", headers=headers) for _ in range(limit)]
    blocked = client.post("/probe", headers=headers)

    # All requests up to the limit pass; the next one is throttled. Because every
    # request flows through the same app.state backend, this also proves the counter
    # is shared across requests (no per-request reset).
    assert [resp.status_code for resp in allowed] == [200] * limit
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


@pytest.mark.parametrize(("dep", "limit"), CASES, ids=_CASE_IDS)
def test_enforce_isolates_tenants(dep: Callable[..., object], limit: int) -> None:
    client = _probe_client(dep)

    for _ in range(limit):
        assert client.post("/probe", headers=_headers(TENANT_A)).status_code == 200
    assert client.post("/probe", headers=_headers(TENANT_A)).status_code == 429

    # Same app/backend, different tenant key -> independent counter.
    assert client.post("/probe", headers=_headers(TENANT_B)).status_code == 200


# (path, method, expected enforce dependency) for each real route. Paths verified
# against the routers: auth prefix /auth; imports /api/v1/imports; campaigns
# /api/v1/campaigns; sending uses absolute paths; followups /api/v1/followups.
WIRING: list[tuple[str, str, Callable[..., object]]] = [
    ("/auth/session", "POST", enforce_auth_session_rate_limit),
    ("/api/v1/imports/contacts", "POST", enforce_import_rate_limit),
    ("/api/v1/campaigns", "POST", enforce_campaign_create_rate_limit),
    (
        "/api/v1/campaigns/{campaign_id}/contacts",
        "POST",
        enforce_campaign_contact_select_rate_limit,
    ),
    ("/api/v1/send-gate/dry-run", "POST", enforce_send_gate_rate_limit),
    ("/api/v1/send-intents", "POST", enforce_send_intent_rate_limit),
    ("/api/v1/followups/rules", "POST", enforce_followup_rate_limit),
    ("/api/v1/followups/schedules", "POST", enforce_followup_rate_limit),
    (
        "/api/v1/followups/schedules/{schedule_id}/mock-run",
        "POST",
        enforce_followup_rate_limit,
    ),
]
_WIRING_IDS = [f"{method} {path}" for path, method, _ in WIRING]


def _dependant_has(dependant: object, dep: Callable[..., object]) -> bool:
    """Recursively scan a route's dependant tree for ``dep``."""
    deps = getattr(dependant, "dependencies", [])
    if any(sub.call is dep for sub in deps):
        return True
    return any(_dependant_has(sub, dep) for sub in deps)


def _find_route(app: FastAPI, path: str, method: str) -> APIRoute | None:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    return None


@pytest.mark.parametrize(("path", "method", "dep"), WIRING, ids=_WIRING_IDS)
def test_real_route_carries_rate_limit_dependency(
    path: str, method: str, dep: Callable[..., object]
) -> None:
    app = create_app()

    route = _find_route(app, path, method)

    assert route is not None, f"route not found: {method} {path}"
    assert _dependant_has(route.dependant, dep), f"{dep.__name__} not wired on {method} {path}"
