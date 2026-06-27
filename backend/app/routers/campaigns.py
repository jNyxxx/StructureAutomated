"""Campaign read/create API (Phase 2 P2-2).

Exposes only mature campaign paths. Research/runs, drafts, sending, webhooks,
providers, and frontend wiring remain deferred.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
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
from app.ratelimit.dependencies import (
    enforce_campaign_contact_select_rate_limit,
    enforce_campaign_create_rate_limit,
)
from app.repositories.billing_repo import BillingRepository
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.schemas.campaigns import (
    CampaignContactSelectionResponse,
    CampaignContactSelectRequest,
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignDetailResponse,
    CampaignDTO,
    CampaignListResponse,
    CampaignUpdateRequest,
    CampaignUpdateResponse,
)
from app.schemas.pagination import PageInfo, PageParams
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import BillingGateService
from app.services.campaign import CampaignRecord, CampaignService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])

IDEMPOTENCY_HEADER = "idempotency-key"


def idempotency_key(request: Request) -> str:
    """Require a non-blank Idempotency-Key header for campaign creation."""
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required.",
            status_code=400,
        )
    return raw.strip()


async def campaign_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[CampaignService]:
    """Build CampaignService inside a tenant-scoped DB transaction."""
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        yield CampaignService(
            store=CampaignRepository(conn),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
            billing=BillingGateService(BillingRepository(conn)),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            audit_record=audit.record,
        )


def _campaign_page(records: Sequence[CampaignRecord], page: PageParams) -> CampaignListResponse:
    start = 0
    if page.cursor is not None:
        try:
            cursor_id = uuid.UUID(page.cursor)
        except ValueError:
            return CampaignListResponse(
                campaigns=[], page=PageInfo(next_cursor=None, limit=page.limit)
            )
        ids = [record.id for record in records]
        if cursor_id not in ids:
            return CampaignListResponse(
                campaigns=[], page=PageInfo(next_cursor=None, limit=page.limit)
            )
        start = ids.index(cursor_id) + 1

    window = list(records[start : start + page.limit + 1])
    items = window[: page.limit]
    next_cursor = str(items[-1].id) if len(window) > page.limit and items else None
    return CampaignListResponse(
        campaigns=[CampaignDTO.from_record(record) for record in items],
        page=PageInfo(next_cursor=next_cursor, limit=page.limit),
    )


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[CampaignService, Depends(campaign_service)],
) -> CampaignListResponse:
    """List tenant campaigns using the existing mature CampaignService."""
    campaigns = await service.list_campaigns(principal=principal)
    return _campaign_page(campaigns, page)


@router.post("", status_code=201, response_model=CampaignCreateResponse)
async def create_campaign(
    body: CampaignCreateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    _rate_limit: Annotated[None, Depends(enforce_campaign_create_rate_limit)],
    service: Annotated[CampaignService, Depends(campaign_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> CampaignCreateResponse:
    """Create a tenant campaign. Gates and idempotency are enforced by the service."""
    try:
        result = await service.create_campaign(
            principal=principal,
            name=body.name,
            description=body.description,
            goal=body.goal,
            target_segment=body.target_segment,
            notes=body.notes,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return CampaignCreateResponse.from_result(result)


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[CampaignService, Depends(campaign_service)],
) -> CampaignDetailResponse:
    """Return one tenant-scoped campaign."""
    campaign = await service.get_campaign(principal=principal, campaign_id=campaign_id)
    return CampaignDetailResponse.from_record(campaign)


@router.patch("/{campaign_id}", response_model=CampaignUpdateResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    body: CampaignUpdateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[CampaignService, Depends(campaign_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> CampaignUpdateResponse:
    """Update basic campaign metadata/status with idempotency."""
    try:
        result = await service.update_campaign_idempotent(
            principal=principal,
            campaign_id=campaign_id,
            name=body.name,
            description=body.description,
            goal=body.goal,
            target_segment=body.target_segment,
            notes=body.notes,
            status=body.status,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return CampaignUpdateResponse.from_result(result)


@router.post(
    "/{campaign_id}/contacts",
    status_code=201,
    response_model=CampaignContactSelectionResponse,
)
async def select_campaign_contact(
    campaign_id: uuid.UUID,
    body: CampaignContactSelectRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    _rate_limit: Annotated[None, Depends(enforce_campaign_contact_select_rate_limit)],
    service: Annotated[CampaignService, Depends(campaign_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> CampaignContactSelectionResponse:
    """Select a tenant contact for a campaign with idempotency."""
    try:
        result = await service.attach_contact_idempotent(
            principal=principal,
            campaign_id=campaign_id,
            contact_id=body.contact_id,
            status=body.status,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return CampaignContactSelectionResponse.from_result(result)
