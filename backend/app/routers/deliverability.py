"""Mock/local deliverability dashboard API for Phase 2 P2-5."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.contact_repo import ContactReadRepository
from app.repositories.deliverability_repo import DeliverabilityRepository
from app.repositories.outcomes_repo import OutcomesRepository
from app.schemas.deliverability import DeliverabilityResponse, MailboxHealthResponse
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.dashboard import DashboardService
from app.services.deliverability import DeliverabilityService
from app.services.outcomes import OutcomesService

router = APIRouter(prefix="/api/v1/deliverability", tags=["deliverability"])


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


@router.get("", response_model=DeliverabilityResponse)
async def get_deliverability(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DashboardService, Depends(dashboard_service)],
    campaign_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DeliverabilityResponse:
    result = await service.get_deliverability_summary(
        principal,
        campaign_id=campaign_id,
        date_from=date_from,
        date_to=date_to,
    )
    return DeliverabilityResponse.from_result(result)


@router.get("/mailboxes", response_model=MailboxHealthResponse)
def get_mailbox_health(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DashboardService, Depends(dashboard_service)],
) -> MailboxHealthResponse:
    return MailboxHealthResponse.from_result(service.get_mailbox_health(principal))
