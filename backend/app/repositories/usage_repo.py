"""Tenant-scoped usage aggregation for local/mock billing UI.

Counts are derived from existing tables only. This repository does not call
Stripe, payment providers, external APIs, webhooks, or billing meters.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.campaign import Campaign
from app.models.contact import Contact, ContactImport
from app.models.draft import Draft
from app.models.followup import FollowUpSchedule
from app.models.outcomes import OutcomeEvent
from app.models.research import ResearchRun
from app.models.sending import OutboundMessage, SendGateResult
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class UsageSnapshotRecord:
    contacts_total: int
    contact_imports_total: int
    campaigns_total: int
    drafts_total: int
    outbound_mock_sent: int
    outbound_blocked: int
    send_gate_denied: int
    followups_mock_sent: int
    followups_skipped: int
    research_runs_total: int
    outcome_events_total: int


class UsageRepository(BaseRepository):
    """Count-only usage snapshot from tenant-owned local/mock tables."""

    async def _count(self, model: type[Any], tenant_id: uuid.UUID) -> int:
        result = await self.conn.execute(
            select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
        )
        return int(result.scalar_one() or 0)

    async def _count_where(
        self,
        model: type[Any],
        tenant_id: uuid.UUID,
        *conditions: ColumnElement[bool],
    ) -> int:
        result = await self.conn.execute(
            select(func.count()).select_from(model).where(model.tenant_id == tenant_id, *conditions)
        )
        return int(result.scalar_one() or 0)

    async def get_snapshot(self, *, tenant_id: uuid.UUID) -> UsageSnapshotRecord:
        return UsageSnapshotRecord(
            contacts_total=await self._count(Contact, tenant_id),
            contact_imports_total=await self._count(ContactImport, tenant_id),
            campaigns_total=await self._count(Campaign, tenant_id),
            drafts_total=await self._count(Draft, tenant_id),
            outbound_mock_sent=await self._count_where(
                OutboundMessage, tenant_id, OutboundMessage.status == "mock_sent"
            ),
            outbound_blocked=await self._count_where(
                OutboundMessage, tenant_id, OutboundMessage.status == "blocked"
            ),
            send_gate_denied=await self._count_where(
                SendGateResult, tenant_id, SendGateResult.status == "denied"
            ),
            followups_mock_sent=await self._count_where(
                FollowUpSchedule, tenant_id, FollowUpSchedule.status == "mock_sent"
            ),
            followups_skipped=await self._count_where(
                FollowUpSchedule, tenant_id, FollowUpSchedule.status == "skipped"
            ),
            research_runs_total=await self._count(ResearchRun, tenant_id),
            outcome_events_total=await self._count(OutcomeEvent, tenant_id),
        )
