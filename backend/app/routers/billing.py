"""Mock/local billing, usage, and access-gate API for Phase 2 P2-7."""

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
from app.config import get_settings
from app.database import tenant_session
from app.middleware.error_handler import AppError
from app.repositories.billing_repo import BillingRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.repositories.usage_repo import UsageRepository
from app.schemas.billing import (
    BillingAccessResponse,
    BillingStateTransitionRequest,
    BillingStateTransitionResponse,
    BillingSubscriptionResponse,
    UsageResponse,
)
from app.services.authz import RBACService
from app.services.billing import BillingGateService
from app.services.billing_api import BillingAPIService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService

router = APIRouter(tags=["billing"])
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


async def billing_api_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[BillingAPIService]:
    settings = get_settings()
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        billing_repo = BillingRepository(conn)
        yield BillingAPIService(
            billing=BillingGateService(billing_repo, audit.record),
            billing_store=billing_repo,
            usage_store=UsageRepository(conn),
            rbac=RBACService(),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            allow_mock_state_transition=not settings.is_production,
        )


@router.get("/api/v1/billing/subscription", response_model=BillingSubscriptionResponse)
async def get_billing_subscription(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[BillingAPIService, Depends(billing_api_service)],
) -> BillingSubscriptionResponse:
    return BillingSubscriptionResponse.from_record(await service.get_subscription(principal))


@router.get("/api/v1/billing/access", response_model=BillingAccessResponse)
async def get_billing_access(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[BillingAPIService, Depends(billing_api_service)],
) -> BillingAccessResponse:
    return BillingAccessResponse.from_snapshot(
        await service.get_access(principal, now=datetime.now(UTC))
    )


@router.get("/api/v1/usage", response_model=UsageResponse)
async def get_usage(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[BillingAPIService, Depends(billing_api_service)],
) -> UsageResponse:
    return UsageResponse.from_record(await service.get_usage(principal))


@router.post(
    "/api/v1/billing/state-transition",
    response_model=BillingStateTransitionResponse,
)
async def transition_billing_state(
    body: BillingStateTransitionRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[BillingAPIService, Depends(billing_api_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> BillingStateTransitionResponse:
    try:
        result = await service.transition_state_idempotent(
            principal,
            tenant_status=body.tenant_status,
            grace_until=body.grace_until,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return BillingStateTransitionResponse.from_result(result)
