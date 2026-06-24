"""Read-only review queue API for Phase 2 P2-3.

Review approve/reject/regenerate, send-gate, sending, providers, and frontend
wiring remain deferred.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.audit.repository import AuditRepository
from app.audit.service import AuditService
from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.middleware.error_handler import AppError
from app.repositories.billing_repo import BillingRepository
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.contact_repo import ContactReadRepository
from app.repositories.draft_repo import DraftRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.safety_repo import SafetyRepository
from app.schemas.pagination import PageParams
from app.schemas.review import (
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewItemDetailResponse,
    ReviewItemListResponse,
)
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import BillingGateService
from app.services.compliance import ComplianceGateService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService
from app.services.review import ReviewService
from app.services.review_read import ReviewReadService

router = APIRouter(prefix="/api/v1/review/items", tags=["review"])

IDEMPOTENCY_HEADER = "idempotency-key"


class _ContactStoreAdapter:
    def __init__(self, repo: ContactReadRepository) -> None:
        self._repo = repo

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        return await self._repo.get_contact_by_id(tenant_id=tenant_id, contact_id=contact_id)


def idempotency_key(request: Request) -> str:
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required.",
            status_code=400,
        )
    return raw.strip()


async def review_read_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[ReviewReadService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        yield ReviewReadService(
            store=ReviewRepository(conn),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
        )


async def review_action_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[ReviewService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        yield ReviewService(
            review_store=ReviewRepository(conn),
            draft_store=DraftRepository(conn),
            safety_store=SafetyRepository(conn),
            contact_store=_ContactStoreAdapter(ContactReadRepository(conn)),
            billing=BillingGateService(BillingRepository(conn)),
            rbac=RBACService(),
            compliance=ComplianceGateService(ComplianceRepository(conn), audit.record),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            audit_record=audit.record,
        )


@router.get("", response_model=ReviewItemListResponse)
async def list_review_items(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ReviewReadService, Depends(review_read_service)],
    campaign_id: uuid.UUID | None = None,
    status: str | None = None,
) -> ReviewItemListResponse:
    items = await service.list_items(
        principal=principal,
        cursor=page.cursor,
        limit=page.limit,
        campaign_id=campaign_id,
        status=status,
    )
    return ReviewItemListResponse.from_page(items)


@router.get("/{review_id}", response_model=ReviewItemDetailResponse)
async def get_review_item(
    review_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ReviewReadService, Depends(review_read_service)],
) -> ReviewItemDetailResponse:
    item = await service.get_item(principal=principal, review_id=review_id)
    return ReviewItemDetailResponse.from_record(item)


@router.post("/{review_id}/approve", response_model=ReviewActionResponse)
async def approve_review_item(
    review_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ReviewService, Depends(review_action_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> ReviewActionResponse:
    try:
        result = await service.approve_draft_idempotent(
            principal,
            review_id=review_id,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return ReviewActionResponse.from_result(result)


@router.post("/{review_id}/reject", response_model=ReviewActionResponse)
async def reject_review_item(
    review_id: uuid.UUID,
    body: ReviewActionRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ReviewService, Depends(review_action_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> ReviewActionResponse:
    try:
        result = await service.reject_draft_idempotent(
            principal,
            review_id=review_id,
            reason=body.reason,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return ReviewActionResponse.from_result(result)


@router.post("/{review_id}/request-regeneration", response_model=ReviewActionResponse)
async def request_review_item_regeneration(
    review_id: uuid.UUID,
    body: ReviewActionRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ReviewService, Depends(review_action_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> ReviewActionResponse:
    try:
        result = await service.request_regeneration_idempotent(
            principal,
            review_id=review_id,
            reason=body.reason,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return ReviewActionResponse.from_result(result)
