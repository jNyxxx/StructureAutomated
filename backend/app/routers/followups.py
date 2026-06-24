"""Mock/local follow-up API for Phase 2 P2-4b."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.audit.repository import AuditRepository
from app.audit.service import AuditService
from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.middleware.error_handler import AppError
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.repositories.billing_repo import BillingRepository
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.contact_repo import ContactReadRepository
from app.repositories.draft_repo import DraftRepository
from app.repositories.followup_repo import FollowUpRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.safety_repo import SafetyRepository
from app.repositories.sending_repo import SendingRepository
from app.schemas.followups import (
    FollowUpRuleActionResponse,
    FollowUpRuleCreateRequest,
    FollowUpRuleListResponse,
    FollowUpScheduleActionResponse,
    FollowUpScheduleCreateRequest,
    FollowUpScheduleListResponse,
)
from app.schemas.pagination import PageParams
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import BillingGateService
from app.services.compliance import ComplianceGateService
from app.services.followup_scheduler import FollowUpSchedulerService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService
from app.services.rate_limit import RateLimitPolicy, RateLimitService
from app.services.send_gate import SendGateService

router = APIRouter(prefix="/api/v1/followups", tags=["followups"])
IDEMPOTENCY_HEADER = "idempotency-key"


class _ContactStoreAdapter:
    def __init__(self, repo: ContactReadRepository) -> None:
        self._repo = repo

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        return await self._repo.get_contact_by_id(tenant_id=tenant_id, contact_id=contact_id)


class _NoopQueue:
    async def enqueue(self, **kwargs: Any) -> Any:
        raise AppError("QUEUE_DISABLED", "Queue disabled.", status_code=500)


def idempotency_key(request: Request) -> str:
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required.",
            status_code=400,
        )
    return raw.strip()


def _send_gate_service(conn: Any, audit: AuditService) -> SendGateService:
    return SendGateService(
        sending_store=SendingRepository(conn),
        draft_store=DraftRepository(conn),
        review_store=ReviewRepository(conn),
        safety_store=SafetyRepository(conn),
        contact_store=_ContactStoreAdapter(ContactReadRepository(conn)),
        billing=BillingGateService(BillingRepository(conn)),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        compliance=ComplianceGateService(ComplianceRepository(conn), audit.record),
        rate_limiter=RateLimitService(InMemoryRateLimitBackend()),
        rate_limit_policy=RateLimitPolicy(
            "tenant_followup",
            limit=100,
            window=timedelta(minutes=1),
        ),
        audit_record=audit.record,
    )


async def followup_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[FollowUpSchedulerService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        yield FollowUpSchedulerService(
            followup_store=FollowUpRepository(conn),
            campaign_store=CampaignRepository(conn),
            draft_store=DraftRepository(conn),
            queue_service=_NoopQueue(),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
            billing=BillingGateService(BillingRepository(conn)),
            outbound_store=SendingRepository(conn),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            send_gate=_send_gate_service(conn, audit),
            audit_record=audit.record,
        )


@router.get("/rules", response_model=FollowUpRuleListResponse)
async def list_followup_rules(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[FollowUpSchedulerService, Depends(followup_service)],
) -> FollowUpRuleListResponse:
    result = await service.list_followup_rules(
        principal=principal,
        cursor=page.cursor,
        limit=page.limit,
    )
    return FollowUpRuleListResponse.from_page(result)


@router.post("/rules", status_code=201, response_model=FollowUpRuleActionResponse)
async def create_followup_rule(
    body: FollowUpRuleCreateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[FollowUpSchedulerService, Depends(followup_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> FollowUpRuleActionResponse:
    try:
        result = await service.create_followup_rule_idempotent(
            principal,
            campaign_id=body.campaign_id,
            delay_seconds=body.delay_seconds,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return FollowUpRuleActionResponse.from_result(result)


@router.get("/schedules", response_model=FollowUpScheduleListResponse)
async def list_followup_schedules(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[FollowUpSchedulerService, Depends(followup_service)],
) -> FollowUpScheduleListResponse:
    result = await service.list_followup_schedules(
        principal=principal,
        cursor=page.cursor,
        limit=page.limit,
    )
    return FollowUpScheduleListResponse.from_page(result)


@router.post("/schedules", status_code=201, response_model=FollowUpScheduleActionResponse)
async def create_followup_schedule(
    body: FollowUpScheduleCreateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[FollowUpSchedulerService, Depends(followup_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> FollowUpScheduleActionResponse:
    try:
        result = await service.create_manual_schedule_idempotent(
            principal,
            outbound_message_id=body.original_outbound_message_id,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return FollowUpScheduleActionResponse.from_result(result)


@router.post("/schedules/{schedule_id}/mock-run", response_model=FollowUpScheduleActionResponse)
async def mock_run_followup_schedule(
    schedule_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[FollowUpSchedulerService, Depends(followup_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> FollowUpScheduleActionResponse:
    try:
        result = await service.mock_run_schedule_idempotent(
            principal,
            schedule_id=schedule_id,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return FollowUpScheduleActionResponse.from_result(result)
