"""Backend orchestration for mock/local dashboard API routes.

This service keeps routers thin while preserving existing domain-service gates.
It performs only tenant-scoped object lookups and delegates dashboard logic to
DeliverabilityService and OutcomesService. No provider, CRM, payment, DNS,
webhook, scraping, or sending behavior is implemented here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.outcomes_repo import OutcomeEventRecord
from app.services.deliverability import (
    CampaignDeliverabilitySummary,
    DeliverabilityService,
    DeliverabilitySummary,
    MailboxHealthSummary,
)
from app.services.outcomes import (
    CampaignOutcomesSummary,
    OutcomesService,
    OutcomesSummary,
    ROISummary,
)


class CampaignLookupStore(Protocol):
    async def get_campaign(self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Any | None: ...


class ContactLookupStore(Protocol):
    async def get_contact_by_id(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Any | None: ...


class SentCountStore(Protocol):
    async def get_sent_count(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int: ...


@dataclass(frozen=True)
class DeliverabilityDashboardResult:
    summary: DeliverabilitySummary | CampaignDeliverabilitySummary
    mock_only: bool = True


@dataclass(frozen=True)
class MailboxDashboardResult:
    health: MailboxHealthSummary
    mock_only: bool = True


@dataclass(frozen=True)
class OutcomesDashboardResult:
    summary: OutcomesSummary | CampaignOutcomesSummary
    mock_only: bool = True


@dataclass(frozen=True)
class ROIDashboardResult:
    summary: ROISummary
    mock_only: bool = True


@dataclass(frozen=True)
class MockOutcomeEventResult:
    event: OutcomeEventRecord
    mock_only: bool = True


class DashboardService:
    """Thin service facade for mock/local dashboard API endpoints."""

    def __init__(
        self,
        *,
        deliverability: DeliverabilityService,
        outcomes: OutcomesService,
        campaign_store: CampaignLookupStore,
        contact_store: ContactLookupStore,
        sent_count_store: SentCountStore,
    ) -> None:
        self._deliverability = deliverability
        self._outcomes = outcomes
        self._campaign_store = campaign_store
        self._contact_store = contact_store
        self._sent_count_store = sent_count_store

    async def get_deliverability_summary(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> DeliverabilityDashboardResult:
        summary: DeliverabilitySummary | CampaignDeliverabilitySummary
        if campaign_id is None:
            summary = await self._deliverability.get_tenant_summary(
                principal,
                date_from=date_from,
                date_to=date_to,
            )
        else:
            campaign = await self._campaign_store.get_campaign(
                tenant_id=principal.tenant_id,
                campaign_id=campaign_id,
            )
            if campaign is None:
                raise AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
            summary = await self._deliverability.get_campaign_summary(
                principal,
                campaign_id=campaign_id,
                campaign_tenant_id=campaign.tenant_id,
                date_from=date_from,
                date_to=date_to,
            )
        return DeliverabilityDashboardResult(summary=summary)

    def get_mailbox_health(self, principal: CurrentPrincipal) -> MailboxDashboardResult:
        return MailboxDashboardResult(health=self._deliverability.get_mailbox_health(principal))

    async def get_outcomes_summary(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> OutcomesDashboardResult:
        summary: OutcomesSummary | CampaignOutcomesSummary
        if campaign_id is None:
            summary = await self._outcomes.get_tenant_summary(
                principal,
                date_from=date_from,
                date_to=date_to,
            )
        else:
            campaign = await self._campaign_store.get_campaign(
                tenant_id=principal.tenant_id,
                campaign_id=campaign_id,
            )
            if campaign is None:
                raise AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
            summary = await self._outcomes.get_campaign_summary(
                principal,
                campaign_id=campaign_id,
                campaign_tenant_id=campaign.tenant_id,
                date_from=date_from,
                date_to=date_to,
            )
        return OutcomesDashboardResult(summary=summary)

    async def get_roi_summary(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID,
    ) -> ROIDashboardResult:
        campaign = await self._campaign_store.get_campaign(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
        )
        if campaign is None:
            raise AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
        sent_count = await self._sent_count_store.get_sent_count(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=None,
            date_to=None,
        )
        summary = await self._outcomes.get_roi_summary(
            principal,
            campaign_id=campaign_id,
            campaign_tenant_id=campaign.tenant_id,
            sent_count=sent_count,
        )
        return ROIDashboardResult(summary=summary)

    async def record_mock_outcome_event(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        event_type: str,
        outbound_message_id: uuid.UUID | None,
        note: str | None,
        occurred_at: datetime | None,
        idempotency_key: str,
    ) -> MockOutcomeEventResult:
        campaign = await self._campaign_store.get_campaign(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
        )
        if campaign is None:
            raise AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
        contact = await self._contact_store.get_contact_by_id(
            tenant_id=principal.tenant_id,
            contact_id=contact_id,
        )
        if contact is None:
            raise AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
        namespaced_key = f"{principal.tenant_id}:mock_outcome:{idempotency_key}"
        event = await self._outcomes.record_outcome_event(
            principal,
            campaign_id=campaign_id,
            campaign_tenant_id=campaign.tenant_id,
            contact_id=contact_id,
            contact_tenant_id=contact.tenant_id,
            event_type=event_type,
            outbound_message_id=outbound_message_id,
            note=note,
            idempotency_key=namespaced_key,
            occurred_at=occurred_at,
        )
        return MockOutcomeEventResult(event=event)
