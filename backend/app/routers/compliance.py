"""Mock/local compliance profile and suppression API for Phase 2 P2-6."""

from __future__ import annotations

import uuid
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
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.schemas.compliance import (
    ComplianceProfileActionResponse,
    ComplianceProfileResponse,
    ComplianceProfileUpdateRequest,
    SuppressionActionResponse,
    SuppressionCreateRequest,
    SuppressionListResponse,
)
from app.schemas.pagination import PageInfo, PageParams
from app.services.authz import RBACService
from app.services.compliance import ComplianceGateService
from app.services.compliance_api import ComplianceAPIService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService

router = APIRouter(tags=["compliance"])
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


async def compliance_api_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[ComplianceAPIService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        repo = ComplianceRepository(conn)
        yield ComplianceAPIService(
            compliance=ComplianceGateService(repo, audit.record),
            store=repo,
            rbac=RBACService(),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
        )


@router.get("/api/v1/compliance/profile", response_model=ComplianceProfileResponse)
async def get_compliance_profile(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ComplianceAPIService, Depends(compliance_api_service)],
) -> ComplianceProfileResponse:
    return ComplianceProfileResponse.from_record(await service.get_profile(principal))


@router.put("/api/v1/compliance/profile", response_model=ComplianceProfileActionResponse)
async def update_compliance_profile(
    body: ComplianceProfileUpdateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ComplianceAPIService, Depends(compliance_api_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> ComplianceProfileActionResponse:
    try:
        result = await service.update_profile_idempotent(
            principal,
            idempotency_key=key,
            now=datetime.now(UTC),
            jurisdiction=body.jurisdiction,
            sending_review_required=body.sending_review_required,
            live_sending_allowed=body.live_sending_allowed,
            sms_allowed=body.sms_allowed,
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return ComplianceProfileActionResponse.from_result(result)


@router.get("/api/v1/suppressions", response_model=SuppressionListResponse)
async def list_suppressions(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ComplianceAPIService, Depends(compliance_api_service)],
) -> SuppressionListResponse:
    result = await service.list_suppressions(
        principal,
        cursor=page.cursor,
        limit=page.limit,
    )
    from app.schemas.compliance import SuppressionDTO

    return SuppressionListResponse(
        suppressions=[SuppressionDTO.from_record(row) for row in result.items],
        page=PageInfo(next_cursor=result.next_cursor, limit=result.limit),
    )


@router.post("/api/v1/suppressions", status_code=201, response_model=SuppressionActionResponse)
async def create_suppression(
    body: SuppressionCreateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ComplianceAPIService, Depends(compliance_api_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> SuppressionActionResponse:
    try:
        result = await service.add_suppression_idempotent(
            principal,
            idempotency_key=key,
            now=datetime.now(UTC),
            channel=body.channel,
            contact_identifier=body.contact_identifier,
            reason=body.reason,
            source=body.source,
            never_contact=body.never_contact,
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return SuppressionActionResponse.from_result(result)


@router.post(
    "/api/v1/suppressions/{suppression_id}/reinstate",
    response_model=SuppressionActionResponse,
)
async def reinstate_suppression(
    suppression_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ComplianceAPIService, Depends(compliance_api_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> SuppressionActionResponse:
    try:
        result = await service.reinstate_suppression_idempotent(
            principal,
            suppression_id=suppression_id,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return SuppressionActionResponse.from_result(result)
