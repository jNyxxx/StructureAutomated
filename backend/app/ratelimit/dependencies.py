"""Shared rate-limit dependencies for route-level abuse protection.

Endpoint limits must share a backend for the lifetime of the app process. A fresh
``InMemoryRateLimitBackend`` per request silently disables limits because every
request starts with an empty counter store.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import Depends
from starlette.requests import Request

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.services.rate_limit import DEFAULT_POLICIES, RateLimitPolicy, RateLimitService

TENANT_SEND_POLICY = RateLimitPolicy("tenant_send", limit=100, window=timedelta(minutes=1))
TENANT_FOLLOWUP_POLICY = RateLimitPolicy("tenant_followup", limit=60, window=timedelta(minutes=1))

_fallback_backend = InMemoryRateLimitBackend()
_fallback_service = RateLimitService(_fallback_backend)


def get_process_rate_limit_service() -> RateLimitService:
    """Return the process singleton used when no FastAPI app state is available."""
    return _fallback_service


def get_rate_limit_service(request: Request) -> RateLimitService:
    """Return the app-scoped rate limiter, falling back to a module singleton.

    ``create_app`` wires ``app.state.rate_limit_service``. The fallback keeps
    isolated router tests production-shaped without reintroducing per-request
    counters.
    """
    service = getattr(request.app.state, "rate_limit_service", None)
    if service is not None:
        return cast(RateLimitService, service)
    return get_process_rate_limit_service()


def _client_ip(request: Request) -> str:
    if request.client is None or not request.client.host:
        return "unknown"
    return request.client.host


async def enforce_auth_session_rate_limit(
    request: Request,
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> None:
    """Throttle auth session exchange by IP and hashed auth identifier.

    The raw Authorization header is never stored in the key: ``RateLimitService``
    hashes free-text identifiers before building the counter key.
    """
    policy = DEFAULT_POLICIES["auth"]
    now = datetime.now(UTC)
    ip = _client_ip(request)
    await rate_limiter.enforce(policy, now=now, ip=ip, action="session")

    identifier = request.headers.get("authorization")
    if identifier:
        await rate_limiter.enforce(
            policy,
            now=now,
            ip=ip,
            action="session_identifier",
            identifier=identifier,
        )


async def enforce_import_rate_limit(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> None:
    await rate_limiter.enforce(
        DEFAULT_POLICIES["import"],
        now=datetime.now(UTC),
        tenant_id=str(principal.tenant_id),
        action="contacts_import",
    )


async def enforce_campaign_create_rate_limit(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> None:
    await rate_limiter.enforce(
        DEFAULT_POLICIES["risky_action"],
        now=datetime.now(UTC),
        tenant_id=str(principal.tenant_id),
        action="campaign_create",
    )


async def enforce_campaign_contact_select_rate_limit(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> None:
    await rate_limiter.enforce(
        DEFAULT_POLICIES["risky_action"],
        now=datetime.now(UTC),
        tenant_id=str(principal.tenant_id),
        action="campaign_contact_select",
    )


async def enforce_send_gate_rate_limit(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> None:
    await rate_limiter.enforce(
        TENANT_SEND_POLICY,
        now=datetime.now(UTC),
        tenant_id=str(principal.tenant_id),
        action="send_gate_dry_run",
    )


async def enforce_send_intent_rate_limit(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> None:
    await rate_limiter.enforce(
        TENANT_SEND_POLICY,
        now=datetime.now(UTC),
        tenant_id=str(principal.tenant_id),
        action="send_intent",
    )


async def enforce_followup_rate_limit(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> None:
    await rate_limiter.enforce(
        TENANT_FOLLOWUP_POLICY,
        now=datetime.now(UTC),
        tenant_id=str(principal.tenant_id),
        action="followup_mutation",
    )
