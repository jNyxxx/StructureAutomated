"""Mock/local outcomes and ROI dashboard API for Phase 2 P2-5."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.middleware.error_handler import AppError
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.contact_repo import ContactReadRepository
from app.repositories.deliverability_repo import DeliverabilityRepository
from app.repositories.outcomes_repo import OutcomesRepository
from app.schemas.outcomes import (
    MockOutcomeEventRequest,
    MockOutcomeEventResponse,
    OutcomesResponse,
    ROIResponse,
)
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.dashboard import DashboardService
from app.services.deliverability import DeliverabilityService
from app.services.outcomes import OutcomesService

router = APIRouter(prefix="/api/v1/outcomes", tags=["outcomes"])
IDEMPOTENCY_HEADER = "idempotency-key"


class _SentCountAdapter:
    def __init__(self, repo: DeliverabilityRepository) -> None:
        self._repo = repo

    async def get_sent_count(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        counts = await self._repo.get_outbound_counts(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
        return counts.sent


def idempotency_key(request: Request) -> str:
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required.",
            status_code=400,
        )
    return raw.strip()


async def dashboard_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[DashboardService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        rbac = RBACService()
        object_authz = ObjectAuthorizationService()
        deliverability_repo = DeliverabilityRepository(conn)
        yield DashboardService(
            deliverability=DeliverabilityService(
                store=deliverability_repo,
                rbac=rbac,
                object_authz=object_authz,
            ),
            outcomes=OutcomesService(
                store=OutcomesRepository(conn),
                send_count_store=_SentCountAdapter(deliverability_repo),
                rbac=rbac,
                object_authz=object_authz,
            ),
            campaign_store=CampaignRepository(conn),
            contact_store=ContactReadRepository(conn),
            sent_count_store=_SentCountAdapter(deliverability_repo),
        )


@router.get("", response_model=OutcomesResponse)
async def get_outcomes(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DashboardService, Depends(dashboard_service)],
    campaign_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> OutcomesResponse:
    result = await service.get_outcomes_summary(
        principal,
        campaign_id=campaign_id,
        date_from=date_from,
        date_to=date_to,
    )
    return OutcomesResponse.from_result(result)


@router.get("/roi", response_model=ROIResponse)
async def get_roi(
    campaign_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DashboardService, Depends(dashboard_service)],
) -> ROIResponse:
    result = await service.get_roi_summary(principal, campaign_id=campaign_id)
    return ROIResponse.from_result(result)


@router.post("/mock-events", status_code=201, response_model=MockOutcomeEventResponse)
async def create_mock_outcome_event(
    body: MockOutcomeEventRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DashboardService, Depends(dashboard_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> MockOutcomeEventResponse:
    result = await service.record_mock_outcome_event(
        principal,
        campaign_id=body.campaign_id,
        contact_id=body.contact_id,
        event_type=body.event_type,
        outbound_message_id=body.outbound_message_id,
        note=body.note,
        occurred_at=body.occurred_at,
        idempotency_key=key,
    )
    return MockOutcomeEventResponse.from_result(result)
