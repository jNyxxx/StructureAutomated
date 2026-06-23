"""Outcomes/ROI dashboard data service (Phase 1 Slice P1-12).

Aggregates mock campaign outcome events from outcome_events and
campaign_roi_assumptions into structured DTOs for a future frontend dashboard.

Billing gate: NOT applied for read-only dashboard summary operations (same
pattern as DeliverabilityService). Any route wrapping this service should
require at minimum CAN_READ_DASHBOARD.

For the record_outcome_event write path, CAN_RUN_CAMPAIGN is required (the
agent/workflow that registers outcomes is running the campaign).

No real CRM, payment, ad-platform, SMTP, or live provider is used.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.outcomes_repo import (
    OutcomeEventRecord,
    OutcomeTrendPoint,
    OutcomeTypeCounts,
    ROIAssumptionsRecord,
)
from app.services.authz import (
    CAN_READ_DASHBOARD,
    CAN_RUN_CAMPAIGN,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutcomesSummary:
    """Tenant-level outcomes summary."""

    tenant_id: uuid.UUID
    reply_count: int
    positive_reply_count: int
    meeting_booked_count: int
    opportunity_count: int
    deal_won_count: int
    deal_lost_count: int
    unsubscribe_count: int
    bounce_count: int
    complaint_count: int
    reply_rate: float
    positive_reply_rate: float
    meeting_rate: float
    opportunity_rate: float
    win_rate: float
    date_from: datetime | None
    date_to: datetime | None


@dataclass(frozen=True)
class CampaignOutcomesSummary:
    """Campaign-level outcomes summary."""

    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    reply_count: int
    positive_reply_count: int
    meeting_booked_count: int
    opportunity_count: int
    deal_won_count: int
    deal_lost_count: int
    unsubscribe_count: int
    bounce_count: int
    complaint_count: int
    reply_rate: float
    positive_reply_rate: float
    meeting_rate: float
    opportunity_rate: float
    win_rate: float
    date_from: datetime | None
    date_to: datetime | None


@dataclass(frozen=True)
class ROISummary:
    """Deterministic ROI summary from mock assumptions."""

    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    sent_count: int
    estimated_cost_cents: int
    estimated_pipeline_value_cents: int
    estimated_won_value_cents: int
    # roi_percent = (won_value - cost) / cost * 100; None if cost == 0
    estimated_roi_percent: float | None


@dataclass(frozen=True)
class FunnelSummary:
    """Conversion funnel from sends → reply → meeting → opportunity → won."""

    tenant_id: uuid.UUID
    campaign_id: uuid.UUID | None
    sent: int
    replied: int
    meeting_booked: int
    opportunity: int
    deal_won: int
    # Conversion rates between stages (None when denominator is 0).
    sent_to_reply_rate: float | None
    reply_to_meeting_rate: float | None
    meeting_to_opportunity_rate: float | None
    opportunity_to_win_rate: float | None


# ---------------------------------------------------------------------------
# Store Protocol
# ---------------------------------------------------------------------------


class OutcomesStore(Protocol):
    async def create_outcome_event(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        event_type: str,
        outbound_message_id: uuid.UUID | None,
        note: str | None,
        idempotency_key: str | None,
        occurred_at: datetime | None,
    ) -> OutcomeEventRecord: ...

    async def get_outcome_event(
        self, *, tenant_id: uuid.UUID, event_id: uuid.UUID
    ) -> OutcomeEventRecord | None: ...

    async def get_outcome_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> OutcomeTypeCounts: ...

    async def upsert_roi_assumptions(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        cost_per_send_cents: int,
        pipeline_value_per_opportunity_cents: int,
        revenue_per_deal_won_cents: int,
    ) -> ROIAssumptionsRecord: ...

    async def get_roi_assumptions(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> ROIAssumptionsRecord | None: ...

    async def get_outcome_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[OutcomeTrendPoint]: ...


class SendCountStore(Protocol):
    """Minimal interface for reading sent-message counts needed for rate denominators."""

    async def get_sent_count(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _safe_rate_opt(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _build_outcomes_summary(
    tenant_id: uuid.UUID,
    counts: OutcomeTypeCounts,
    sent: int,
    date_from: datetime | None,
    date_to: datetime | None,
) -> OutcomesSummary:
    return OutcomesSummary(
        tenant_id=tenant_id,
        reply_count=counts.reply_received,
        positive_reply_count=counts.positive_reply,
        meeting_booked_count=counts.meeting_booked,
        opportunity_count=counts.opportunity_created,
        deal_won_count=counts.deal_won,
        deal_lost_count=counts.deal_lost,
        unsubscribe_count=counts.unsubscribed,
        bounce_count=counts.bounced,
        complaint_count=counts.complaint,
        reply_rate=_safe_rate(counts.reply_received, sent),
        positive_reply_rate=_safe_rate(counts.positive_reply, sent),
        meeting_rate=_safe_rate(counts.meeting_booked, sent),
        opportunity_rate=_safe_rate(counts.opportunity_created, sent),
        win_rate=_safe_rate(
            counts.deal_won,
            counts.opportunity_created if counts.opportunity_created > 0 else sent,
        ),
        date_from=date_from,
        date_to=date_to,
    )


def _build_campaign_outcomes_summary(
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    counts: OutcomeTypeCounts,
    sent: int,
    date_from: datetime | None,
    date_to: datetime | None,
) -> CampaignOutcomesSummary:
    return CampaignOutcomesSummary(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        reply_count=counts.reply_received,
        positive_reply_count=counts.positive_reply,
        meeting_booked_count=counts.meeting_booked,
        opportunity_count=counts.opportunity_created,
        deal_won_count=counts.deal_won,
        deal_lost_count=counts.deal_lost,
        unsubscribe_count=counts.unsubscribed,
        bounce_count=counts.bounced,
        complaint_count=counts.complaint,
        reply_rate=_safe_rate(counts.reply_received, sent),
        positive_reply_rate=_safe_rate(counts.positive_reply, sent),
        meeting_rate=_safe_rate(counts.meeting_booked, sent),
        opportunity_rate=_safe_rate(counts.opportunity_created, sent),
        win_rate=_safe_rate(
            counts.deal_won,
            counts.opportunity_created if counts.opportunity_created > 0 else sent,
        ),
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class OutcomesService:
    """Outcomes/ROI dashboard aggregation service.

    Write path (record_outcome_event): requires CAN_RUN_CAMPAIGN.
    Read paths (summaries): require CAN_READ_DASHBOARD.
    No real CRM/payment/provider is called in any path.
    """

    def __init__(
        self,
        *,
        store: OutcomesStore,
        send_count_store: SendCountStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
    ) -> None:
        self._store = store
        self._send_count_store = send_count_store
        self._rbac = rbac
        self._object_authz = object_authz

    # ------------------------------------------------------------------
    # Write: record a new outcome event
    # ------------------------------------------------------------------

    async def record_outcome_event(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID,
        campaign_tenant_id: uuid.UUID,
        contact_id: uuid.UUID,
        contact_tenant_id: uuid.UUID,
        event_type: str,
        outbound_message_id: uuid.UUID | None = None,
        note: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: datetime | None = None,
    ) -> OutcomeEventRecord:
        """Record one outcome event with tenant + object authorization checks."""
        # 1. RBAC
        self._rbac.require(principal, CAN_RUN_CAMPAIGN)

        # 2. Campaign must belong to same tenant
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign_tenant_id),
        )

        # 3. Contact must belong to same tenant
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=contact_id, tenant_id=contact_tenant_id),
        )

        # 4. Validate event_type
        from app.models.outcomes import OUTCOME_EVENT_TYPES

        if event_type not in OUTCOME_EVENT_TYPES:
            raise AppError(
                "INVALID_OUTCOME_EVENT_TYPE",
                f"event_type '{event_type}' is not a recognised outcome event type.",
                status_code=400,
            )

        # 5. Note is allowed but must not contain raw secrets (minimal payload).
        # We strip None; no further validation needed at service layer.

        return await self._store.create_outcome_event(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            event_type=event_type,
            outbound_message_id=outbound_message_id,
            note=note,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at,
        )

    # ------------------------------------------------------------------
    # Read: ROI assumptions upsert (write) + read
    # ------------------------------------------------------------------

    async def set_roi_assumptions(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID,
        campaign_tenant_id: uuid.UUID,
        cost_per_send_cents: int,
        pipeline_value_per_opportunity_cents: int,
        revenue_per_deal_won_cents: int,
    ) -> ROIAssumptionsRecord:
        """Create or update ROI cost/value assumptions for a campaign."""
        self._rbac.require(principal, CAN_RUN_CAMPAIGN)
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign_tenant_id),
        )
        if cost_per_send_cents < 0:
            raise AppError(
                "INVALID_ROI_VALUE", "cost_per_send_cents must be >= 0.", status_code=400
            )

        if pipeline_value_per_opportunity_cents < 0:
            raise AppError(
                "INVALID_ROI_VALUE",
                "pipeline_value_per_opportunity_cents must be >= 0.",
                status_code=400,
            )
        if revenue_per_deal_won_cents < 0:
            raise AppError(
                "INVALID_ROI_VALUE", "revenue_per_deal_won_cents must be >= 0.", status_code=400
            )
        return await self._store.upsert_roi_assumptions(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            cost_per_send_cents=cost_per_send_cents,
            pipeline_value_per_opportunity_cents=pipeline_value_per_opportunity_cents,
            revenue_per_deal_won_cents=revenue_per_deal_won_cents,
        )

    # ------------------------------------------------------------------
    # Read: Summaries
    # ------------------------------------------------------------------

    async def get_tenant_summary(
        self,
        principal: CurrentPrincipal,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> OutcomesSummary:
        """Tenant-level outcomes summary. Read-only; requires CAN_READ_DASHBOARD."""
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        counts = await self._store.get_outcome_counts(
            tenant_id=principal.tenant_id,
            campaign_id=None,
            date_from=date_from,
            date_to=date_to,
        )
        sent = await self._send_count_store.get_sent_count(
            tenant_id=principal.tenant_id,
            campaign_id=None,
            date_from=date_from,
            date_to=date_to,
        )
        return _build_outcomes_summary(
            tenant_id=principal.tenant_id,
            counts=counts,
            sent=sent,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_campaign_summary(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID,
        campaign_tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> CampaignOutcomesSummary:
        """Campaign-level outcomes summary. Requires CAN_READ_DASHBOARD + tenant ownership."""
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign_tenant_id),
        )
        counts = await self._store.get_outcome_counts(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
        sent = await self._send_count_store.get_sent_count(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
        return _build_campaign_outcomes_summary(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            counts=counts,
            sent=sent,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_roi_summary(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID,
        campaign_tenant_id: uuid.UUID,
        sent_count: int,
    ) -> ROISummary:
        """Return deterministic ROI calculation from stored assumptions + outcome counts.

        If no assumptions are configured, all cost/value figures will be zero.
        """
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign_tenant_id),
        )
        assumptions = await self._store.get_roi_assumptions(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        counts = await self._store.get_outcome_counts(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=None,
            date_to=None,
        )

        if assumptions is not None:
            cost = sent_count * assumptions.cost_per_send_cents
            pipeline = counts.opportunity_created * assumptions.pipeline_value_per_opportunity_cents
            won = counts.deal_won * assumptions.revenue_per_deal_won_cents
        else:
            cost = pipeline = won = 0

        roi_pct: float | None = None
        if cost > 0:
            roi_pct = round((won - cost) / cost * 100, 2)

        return ROISummary(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            sent_count=sent_count,
            estimated_cost_cents=cost,
            estimated_pipeline_value_cents=pipeline,
            estimated_won_value_cents=won,
            estimated_roi_percent=roi_pct,
        )

    async def get_funnel_summary(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID | None,
        campaign_tenant_id: uuid.UUID | None,
        sent_count: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> FunnelSummary:
        """Conversion funnel summary from sends down to deals won."""
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        if campaign_id is not None and campaign_tenant_id is not None:
            self._object_authz.require_tenant_owner(
                principal=principal,
                obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign_tenant_id),
            )
        counts = await self._store.get_outcome_counts(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
        return FunnelSummary(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            sent=sent_count,
            replied=counts.reply_received,
            meeting_booked=counts.meeting_booked,
            opportunity=counts.opportunity_created,
            deal_won=counts.deal_won,
            sent_to_reply_rate=_safe_rate_opt(counts.reply_received, sent_count),
            reply_to_meeting_rate=_safe_rate_opt(counts.meeting_booked, counts.reply_received),
            meeting_to_opportunity_rate=_safe_rate_opt(
                counts.opportunity_created, counts.meeting_booked
            ),
            opportunity_to_win_rate=_safe_rate_opt(counts.deal_won, counts.opportunity_created),
        )

    async def get_trend(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID | None,
        campaign_tenant_id: uuid.UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[OutcomeTrendPoint]:
        """Day-bucketed outcome trends."""
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        if campaign_id is not None and campaign_tenant_id is not None:
            self._object_authz.require_tenant_owner(
                principal=principal,
                obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign_tenant_id),
            )
        return await self._store.get_outcome_trend(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
