"""FastAPI auth dependencies.

Bearer tokens are parsed without logging/echoing the raw token. Tenant selection
is explicit via ``X-Tenant-ID`` and no principal is returned until membership is
resolved by ``AuthService``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends
from starlette.requests import Request

from app.auth.managed import make_managed_auth_service
from app.auth.mfa import enforce_mfa, mfa_required_roles
from app.auth.principal import CurrentPrincipal
from app.config import get_settings
from app.database import auth_context_session
from app.middleware.error_handler import AppError
from app.services.auth import AuthService

AUTHORIZATION_HEADER = "authorization"
TENANT_HEADER = "x-tenant-id"


def bearer_token(request: Request) -> str:
    header = request.headers.get(AUTHORIZATION_HEADER)
    if header is None or not header.startswith("Bearer "):
        raise AppError("UNAUTHENTICATED", "Authentication required.", status_code=401)
    token = header.removeprefix("Bearer ").strip()
    if not token:
        raise AppError("UNAUTHENTICATED", "Authentication required.", status_code=401)
    return token


def selected_tenant_id(request: Request) -> uuid.UUID:
    raw = request.headers.get(TENANT_HEADER)
    if raw is None:
        raise AppError("TENANT_REQUIRED", "Selected tenant is required.", status_code=400)
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise AppError("TENANT_REQUIRED", "Selected tenant is required.", status_code=400) from exc


async def auth_service(request: Request) -> AsyncGenerator[AuthService, None]:
    # Mock path: app.state singleton wired at startup (non-production only)
    mock = getattr(request.app.state, "auth_service", None)
    if mock is not None:
        yield cast(AuthService, mock)
        return

    # Managed path: ClerkJwksVerifier singleton from state; DB repos are per-request
    verifier = getattr(request.app.state, "clerk_verifier", None)
    if verifier is None:
        raise AppError(
            "AUTH_NOT_CONFIGURED", "Authentication service is not configured.", status_code=500
        )

    async with auth_context_session() as conn:
        yield make_managed_auth_service(verifier, conn)


async def current_principal(
    token: Annotated[str, Depends(bearer_token)],
    tenant_id: Annotated[uuid.UUID, Depends(selected_tenant_id)],
    service: Annotated[AuthService, Depends(auth_service)],
) -> CurrentPrincipal:
    principal = await service.resolve_principal(token=token, tenant_id=tenant_id)
    # No-op until platform_admin is added to the RBAC matrix (services/authz.py).
    # Default required_roles = {"platform_admin"}; none of the 7 current roles match.
    enforce_mfa(principal, required_roles=mfa_required_roles(get_settings()))
    return principal
