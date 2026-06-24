"""Mock/local send-gate and send-intent API for Phase 2 P2-4."""

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
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.contact_repo import ContactReadRepository
from app.repositories.draft_repo import DraftRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.safety_repo import SafetyRepository
from app.repositories.sending_repo import SendingRepository
from app.schemas.pagination import PageParams
from app.schemas.sending import (
    OutboundMessageDetailResponse,
    OutboundMessageListResponse,
    SendGateDryRunRequest,
    SendGateDryRunResponse,
    SendIntentRequest,
    SendIntentResponse,
)
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import BillingGateService
from app.services.compliance import ComplianceGateService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService
from app.services.mock_sender import MockSenderService
from app.services.outbound_read import OutboundReadService
from app.services.rate_limit import RateLimitPolicy, RateLimitService
from app.services.send_gate import SendGateService

router = APIRouter(tags=["sending"])

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


def _send_gate_service(
    conn: Any, audit: AuditService, *, with_idempotency: bool
) -> SendGateService:
    idempotency = IdempotencyService(IdempotencyRepository(conn)) if with_idempotency else None
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
        rate_limit_policy=RateLimitPolicy("tenant_send", limit=100, window=timedelta(minutes=1)),
        idempotency=idempotency,
        audit_record=audit.record,
    )


async def send_gate_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[SendGateService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        yield _send_gate_service(conn, audit, with_idempotency=True)


async def mock_sender_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[MockSenderService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        yield MockSenderService(
            sending_store=SendingRepository(conn),
            send_gate=_send_gate_service(conn, audit, with_idempotency=False),
            followups=None,
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            audit_record=audit.record,
        )


async def outbound_read_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[OutboundReadService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        yield OutboundReadService(store=SendingRepository(conn), rbac=RBACService())


@router.post("/api/v1/send-gate/dry-run", response_model=SendGateDryRunResponse)
async def dry_run_send_gate(
    body: SendGateDryRunRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[SendGateService, Depends(send_gate_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> SendGateDryRunResponse:
    try:
        result = await service.evaluate_gate_idempotent(
            principal,
            draft_id=body.draft_id,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return SendGateDryRunResponse.from_result(result)


@router.post("/api/v1/send-intents", status_code=201, response_model=SendIntentResponse)
async def create_send_intent(
    body: SendIntentRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[MockSenderService, Depends(mock_sender_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> SendIntentResponse:
    try:
        result = await service.send_approved_draft_idempotent(
            principal,
            draft_id=body.draft_id,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return SendIntentResponse.from_result(result)


@router.get("/api/v1/outbound-messages", response_model=OutboundMessageListResponse)
async def list_outbound_messages(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[OutboundReadService, Depends(outbound_read_service)],
) -> OutboundMessageListResponse:
    messages = await service.list_messages(
        principal=principal,
        cursor=page.cursor,
        limit=page.limit,
    )
    return OutboundMessageListResponse.from_page(messages)


@router.get("/api/v1/outbound-messages/{message_id}", response_model=OutboundMessageDetailResponse)
async def get_outbound_message(
    message_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[OutboundReadService, Depends(outbound_read_service)],
) -> OutboundMessageDetailResponse:
    message = await service.get_message(principal=principal, message_id=message_id)
    return OutboundMessageDetailResponse.from_record(message)
