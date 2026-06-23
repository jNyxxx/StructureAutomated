"""Repository for deliverability metrics aggregation (Phase 1 Slice P1-11).

Aggregates from existing tables: outbound_messages, send_gate_results,
followup_schedules. No new tables or migration required.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select

from app.models.draft import Draft
from app.models.followup import FollowUpSchedule
from app.models.sending import OutboundMessage, SendGateResult
from app.repositories.base import BaseRepository

_SAFETY_DENY_CODES = (
    "safety_missing",
    "safety_failed",
    "groundedness_missing",
    "groundedness_failed",
)


@dataclass(frozen=True)
class OutboundCounts:
    sent: int
    blocked: int


@dataclass(frozen=True)
class GateCounts:
    duplicate_denied: int
    suppressed: int
    safety_denied: int
    throttled: int


@dataclass(frozen=True)
class FollowupCounts:
    followup_sent: int
    followup_skipped: int


@dataclass(frozen=True)
class DeliverabilityTrendPoint:
    """One time-bucketed row of send activity."""

    bucket_date: date
    sent: int
    blocked: int
    followup_sent: int


class DeliverabilityRepository(BaseRepository):
    """Read-only aggregation queries for deliverability metrics.

    All queries explicitly filter by tenant_id (defense-in-depth on top of
    database-level forced RLS). Campaign-level queries join outbound_messages
    and send_gate_results through drafts to reach campaign_id.
    """

    async def get_outbound_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> OutboundCounts:
        stmt = select(
            func.count().filter(OutboundMessage.status == "mock_sent").label("sent"),
            func.count().filter(OutboundMessage.status == "blocked").label("blocked"),
        ).where(OutboundMessage.tenant_id == tenant_id)

        if campaign_id is not None:
            stmt = stmt.join(Draft, OutboundMessage.draft_id == Draft.id).where(
                Draft.campaign_id == campaign_id
            )
        if date_from is not None:
            stmt = stmt.where(OutboundMessage.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(OutboundMessage.created_at <= date_to)

        row = (await self.conn.execute(stmt)).one()
        return OutboundCounts(sent=row.sent or 0, blocked=row.blocked or 0)

    async def get_gate_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> GateCounts:
        stmt = select(
            func.count()
            .filter(SendGateResult.deny_reason_code == "duplicate_send")
            .label("duplicate_denied"),
            func.count()
            .filter(SendGateResult.deny_reason_code == "contact_suppressed")
            .label("suppressed"),
            func.count()
            .filter(SendGateResult.deny_reason_code.in_(_SAFETY_DENY_CODES))
            .label("safety_denied"),
            func.count().filter(SendGateResult.deny_reason_code == "throttled").label("throttled"),
        ).where(
            SendGateResult.tenant_id == tenant_id,
            SendGateResult.status == "denied",
        )

        if campaign_id is not None:
            stmt = stmt.join(Draft, SendGateResult.draft_id == Draft.id).where(
                Draft.campaign_id == campaign_id
            )
        if date_from is not None:
            stmt = stmt.where(SendGateResult.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(SendGateResult.created_at <= date_to)

        row = (await self.conn.execute(stmt)).one()
        return GateCounts(
            duplicate_denied=row.duplicate_denied or 0,
            suppressed=row.suppressed or 0,
            safety_denied=row.safety_denied or 0,
            throttled=row.throttled or 0,
        )

    async def get_followup_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> FollowupCounts:
        stmt = select(
            func.count().filter(FollowUpSchedule.status == "mock_sent").label("followup_sent"),
            func.count().filter(FollowUpSchedule.status == "skipped").label("followup_skipped"),
        ).where(FollowUpSchedule.tenant_id == tenant_id)

        if campaign_id is not None:
            stmt = stmt.where(FollowUpSchedule.campaign_id == campaign_id)
        if date_from is not None:
            stmt = stmt.where(FollowUpSchedule.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(FollowUpSchedule.created_at <= date_to)

        row = (await self.conn.execute(stmt)).one()
        return FollowupCounts(
            followup_sent=row.followup_sent or 0,
            followup_skipped=row.followup_skipped or 0,
        )

    async def get_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> list[DeliverabilityTrendPoint]:
        """Return daily send activity buckets sorted ascending by date."""
        from sqlalchemy import cast, func
        from sqlalchemy.dialects.postgresql import DATE

        bucket = cast(func.date_trunc("day", OutboundMessage.created_at), DATE).label("bucket_date")
        stmt = (
            select(
                bucket,
                func.count().filter(OutboundMessage.status == "mock_sent").label("sent"),
                func.count().filter(OutboundMessage.status == "blocked").label("blocked"),
            )
            .where(
                OutboundMessage.tenant_id == tenant_id,
                OutboundMessage.created_at >= date_from,
                OutboundMessage.created_at <= date_to,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        om_rows = (await self.conn.execute(stmt)).all()

        # Followup counts bucketed by day of creation
        fu_bucket = cast(func.date_trunc("day", FollowUpSchedule.created_at), DATE).label(
            "bucket_date"
        )
        fu_stmt = (
            select(
                fu_bucket,
                func.count().filter(FollowUpSchedule.status == "mock_sent").label("followup_sent"),
            )
            .where(
                FollowUpSchedule.tenant_id == tenant_id,
                FollowUpSchedule.created_at >= date_from,
                FollowUpSchedule.created_at <= date_to,
            )
            .group_by(fu_bucket)
        )
        fu_rows = (await self.conn.execute(fu_stmt)).all()
        fu_by_date: dict[date, int] = {r.bucket_date: r.followup_sent for r in fu_rows}

        return [
            DeliverabilityTrendPoint(
                bucket_date=r.bucket_date,
                sent=r.sent or 0,
                blocked=r.blocked or 0,
                followup_sent=fu_by_date.get(r.bucket_date, 0),
            )
            for r in om_rows
        ]
