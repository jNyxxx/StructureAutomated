"""Auth/session routes for app-side Clerk mapping and revocation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.auth.dependencies import auth_service, current_principal
from app.auth.principal import CurrentPrincipal
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _principal_payload(principal: CurrentPrincipal) -> dict[str, Any]:
    return {
        "provider_user_id": principal.provider_user_id,
        "user_id": str(principal.user_id),
        "email": principal.email,
        "tenant_id": str(principal.tenant_id),
        "role": principal.role,
        "membership_version": principal.membership_version,
        "mfa_verified": principal.mfa_verified,
    }


@router.post("/session")
async def exchange_session(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> dict[str, Any]:
    return {"principal": _principal_payload(principal)}


@router.get("/me")
async def me(principal: Annotated[CurrentPrincipal, Depends(current_principal)]) -> dict[str, Any]:
    return {"principal": _principal_payload(principal)}


@router.post("/logout")
async def logout(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[AuthService, Depends(auth_service)],
) -> dict[str, Any]:
    revoked = await service.revoke_session(principal, now=datetime.now(UTC))
    return {"revoked": revoked}


@router.post("/logout-all")
async def logout_all(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[AuthService, Depends(auth_service)],
) -> dict[str, Any]:
    revoked = await service.revoke_all_sessions(principal, now=datetime.now(UTC))
    return {"revoked": revoked}
