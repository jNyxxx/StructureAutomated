"""Deliverability dashboard data service (Phase 1 Slice P1-11).

Aggregates mock send outcomes from outbound_messages, send_gate_results, and
followup_schedules into structured summaries for a future frontend dashboard.

Billing gate: NOT applied — this service only reads existing send records and
returns summary counts. No expensive agent work or export is performed. Any
route wrapping this service should require at minimum CAN_READ_DASHBOARD.

Mock engagement rates (bounce/open/complaint/reply) are applied deterministically
to the sent count so the dashboard has realistic-looking data in local/demo mode
without any real provider integration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.repositories.deliverability_repo import (
    DeliverabilityTrendPoint,
    FollowupCounts,
    GateCounts,
    OutboundCounts,
)
from app.services.authz import (
    CAN_READ_DASHBOARD,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)

_MOCK_BOUNCE_RATE = 0.02
_MOCK_COMPLAINT_RATE = 0.005
_MOCK_OPEN_RATE = 0.35
_MOCK_REPLY_RATE = 0.08


@dataclass(frozen=True)
class DeliverabilitySummary:
    """Tenant-level deliverability summary for the dashboard."""

    tenant_id: uuid.UUID
    sent: int
    blocked: int
    duplicate_denied: int
    suppressed: int
    safety_denied: int
    throttled: int
    followup_sent: int
    followup_skipped: int
    mock_bounced: int
    mock_complained: int
    mock_opened: int
    mock_replied: int
    date_from: datetime | None
    date_to: datetime | None


@dataclass(frozen=True)
class CampaignDeliverabilitySummary:
    """Campaign-level deliverability summary for the dashboard."""

    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    sent: int
    blocked: int
    duplicate_denied: int
    suppressed: int
    safety_denied: int
    throttled: int
    followup_sent: int
    followup_skipped: int
    mock_bounced: int
    mock_complained: int
    mock_opened: int
    mock_replied: int
    date_from: datetime | None
    date_to: datetime | None


@dataclass(frozen=True)
class MailboxHealthSummary:
    """Deterministic mock mailbox/domain health for local/demo use."""

    tenant_id: uuid.UUID
    mock_domain: str
    dkim_valid: bool
    spf_valid: bool
    dmarc_valid: bool
    reputation_score: int


class DeliverabilityStore(Protocol):
    """Repository interface consumed by DeliverabilityService."""

    async def get_outbound_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> OutboundCounts: ...

    async def get_gate_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> GateCounts: ...

    async def get_followup_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> FollowupCounts: ...

    async def get_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> list[DeliverabilityTrendPoint]: ...


def _mock_engagement(sent: int) -> tuple[int, int, int, int]:
    """Return (bounced, complained, opened, replied) derived from sent count."""
    return (
        int(sent * _MOCK_BOUNCE_RATE),
        int(sent * _MOCK_COMPLAINT_RATE),
        int(sent * _MOCK_OPEN_RATE),
        int(sent * _MOCK_REPLY_RATE),
    )


class DeliverabilityService:
    """Read-only deliverability dashboard aggregation service."""

    def __init__(
        self,
        *,
        store: DeliverabilityStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
    ) -> None:
        self._store = store
        self._rbac = rbac
        self._object_authz = object_authz

    async def get_tenant_summary(
        self,
        principal: CurrentPrincipal,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> DeliverabilitySummary:
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        om = await self._store.get_outbound_counts(
            tenant_id=principal.tenant_id,
            date_from=date_from,
            date_to=date_to,
        )
        gc = await self._store.get_gate_counts(
            tenant_id=principal.tenant_id,
            date_from=date_from,
            date_to=date_to,
        )
        fc = await self._store.get_followup_counts(
            tenant_id=principal.tenant_id,
            date_from=date_from,
            date_to=date_to,
        )
        bounced, complained, opened, replied = _mock_engagement(om.sent)
        return DeliverabilitySummary(
            tenant_id=principal.tenant_id,
            sent=om.sent,
            blocked=om.blocked,
            duplicate_denied=gc.duplicate_denied,
            suppressed=gc.suppressed,
            safety_denied=gc.safety_denied,
            throttled=gc.throttled,
            followup_sent=fc.followup_sent,
            followup_skipped=fc.followup_skipped,
            mock_bounced=bounced,
            mock_complained=complained,
            mock_opened=opened,
            mock_replied=replied,
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
    ) -> CampaignDeliverabilitySummary:
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign_tenant_id),
        )
        om = await self._store.get_outbound_counts(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
        gc = await self._store.get_gate_counts(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
        fc = await self._store.get_followup_counts(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
        bounced, complained, opened, replied = _mock_engagement(om.sent)
        return CampaignDeliverabilitySummary(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            sent=om.sent,
            blocked=om.blocked,
            duplicate_denied=gc.duplicate_denied,
            suppressed=gc.suppressed,
            safety_denied=gc.safety_denied,
            throttled=gc.throttled,
            followup_sent=fc.followup_sent,
            followup_skipped=fc.followup_skipped,
            mock_bounced=bounced,
            mock_complained=complained,
            mock_opened=opened,
            mock_replied=replied,
            date_from=date_from,
            date_to=date_to,
        )

    def get_mailbox_health(self, principal: CurrentPrincipal) -> MailboxHealthSummary:
        """Return a deterministic mock mailbox/domain health snapshot.

        No DB call, no network call, no real DNS/DKIM/SPF/DMARC checks.
        Score is derived from the tenant UUID so the same tenant always gets
        the same result across calls (useful for dashboard stability in demos).
        """
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        tenant_hash = hash(str(principal.tenant_id)) & 0xFFFF
        reputation_score = 70 + (tenant_hash % 30)
        short_id = str(principal.tenant_id).replace("-", "")[:8]
        return MailboxHealthSummary(
            tenant_id=principal.tenant_id,
            mock_domain=f"mock-{short_id}.example.com",
            dkim_valid=True,
            spf_valid=True,
            dmarc_valid=True,
            reputation_score=reputation_score,
        )

    async def get_trend(
        self,
        principal: CurrentPrincipal,
        *,
        date_from: datetime,
        date_to: datetime,
    ) -> list[DeliverabilityTrendPoint]:
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        return await self._store.get_trend(
            tenant_id=principal.tenant_id,
            date_from=date_from,
            date_to=date_to,
        )
