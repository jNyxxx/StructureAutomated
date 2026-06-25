"""Local/mock settings, team read, and audit read API for Phase 2 P2-8."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.audit.repository import AuditRepository
from app.audit.service import AuditService
from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.middleware.error_handler import AppError
from app.repositories.idempotency_repo import IdempotencyRepository
from app.repositories.membership_repo import MembershipRepository
from app.repositories.tenant_repo import TenantRepository
from app.schemas.pagination import PageParams
from app.schemas.settings import (
    AuditEventListResponse,
    MembershipListResponse,
    TenantResponse,
    TenantUpdateRequest,
    TenantUpdateResponse,
)
from app.services.authz import RBACService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService
from app.services.settings_api import SettingsAPIService

router = APIRouter(tags=["settings"])
IDEMPOTENCY_HEADER = "idempotency-key"


def idempotency_key(request: Request) -> str:
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required.",
            status_code=400,
        )
    return raw.strip()


async def settings_api_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[SettingsAPIService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit_repo = AuditRepository(conn)
        audit = AuditService(audit_repo)
        yield SettingsAPIService(
            tenants=TenantRepository(conn),
            memberships=MembershipRepository(conn),
            audit_events=audit_repo,
            rbac=RBACService(),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            audit_record=audit.record,
        )


@router.get("/api/v1/tenants/current", response_model=TenantResponse)
async def get_current_tenant(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[SettingsAPIService, Depends(settings_api_service)],
) -> TenantResponse:
    return TenantResponse.from_record(await service.get_current_tenant(principal))


@router.patch("/api/v1/tenants/current", response_model=TenantUpdateResponse)
async def update_current_tenant(
    body: TenantUpdateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[SettingsAPIService, Depends(settings_api_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> TenantUpdateResponse:
    try:
        result = await service.update_current_tenant_idempotent(
            principal,
            idempotency_key=key,
            now=datetime.now(UTC),
            name=body.name,
            settings_patch=body.settings,
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return TenantUpdateResponse.from_result(result)


@router.get("/api/v1/memberships", response_model=MembershipListResponse)
async def list_memberships(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[SettingsAPIService, Depends(settings_api_service)],
) -> MembershipListResponse:
    return MembershipListResponse.from_records(await service.list_memberships(principal))


@router.get("/api/v1/audit-events", response_model=AuditEventListResponse)
async def list_audit_events(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[SettingsAPIService, Depends(settings_api_service)],
) -> AuditEventListResponse:
    result = await service.list_audit_events(
        principal,
        cursor=page.cursor,
        limit=page.limit,
    )
    return AuditEventListResponse.from_page(result)
