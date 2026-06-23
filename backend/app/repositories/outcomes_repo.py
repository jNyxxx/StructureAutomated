"""Repository for outcomes/ROI aggregation (Phase 1 Slice P1-12).

Reads from outcome_events and campaign_roi_assumptions tables.
All queries filter by tenant_id (defence-in-depth on top of forced DB RLS).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select

from app.models.outcomes import CampaignROIAssumptions, OutcomeEvent
from app.repositories.base import BaseRepository

# ---------------------------------------------------------------------------
# Data-transfer objects returned from repo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutcomeEventRecord:
    """Lightweight record returned from outcome_events queries."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    outbound_message_id: uuid.UUID | None
    event_type: str
    note: str | None
    idempotency_key: str | None
    occurred_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class ROIAssumptionsRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    cost_per_send_cents: int
    pipeline_value_per_opportunity_cents: int
    revenue_per_deal_won_cents: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class OutcomeTypeCounts:
    """Raw event-type bucket counts for a given scope."""

    reply_received: int
    positive_reply: int
    meeting_booked: int
    opportunity_created: int
    deal_won: int
    deal_lost: int
    unsubscribed: int
    bounced: int
    complaint: int


class OutcomesRepository(BaseRepository):
    """CRUD + aggregation repository for outcome events and ROI assumptions.

    All queries explicitly include tenant_id (defence-in-depth above DB RLS).
    """

    # ------------------------------------------------------------------
    # Outcome Event CRUD
    # ------------------------------------------------------------------

    async def create_outcome_event(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        event_type: str,
        outbound_message_id: uuid.UUID | None = None,
        note: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: datetime | None = None,
    ) -> OutcomeEventRecord:
        """Insert a new outcome event row.

        If idempotency_key is provided and already exists for this tenant,
        the existing row is returned (upsert-on-conflict style via SELECT).
        """
        if idempotency_key is not None:
            existing = await self._get_by_idempotency_key(
                tenant_id=tenant_id, idempotency_key=idempotency_key
            )
            if existing is not None:
                return existing

        from sqlalchemy import insert

        values: dict = {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "event_type": event_type,
            "outbound_message_id": outbound_message_id,
            "note": note,
            "idempotency_key": idempotency_key,
        }
        if occurred_at is not None:
            values["occurred_at"] = occurred_at

        stmt = (
            insert(OutcomeEvent)
            .values(**values)
            .returning(
                OutcomeEvent.id,
                OutcomeEvent.tenant_id,
                OutcomeEvent.campaign_id,
                OutcomeEvent.contact_id,
                OutcomeEvent.outbound_message_id,
                OutcomeEvent.event_type,
                OutcomeEvent.note,
                OutcomeEvent.idempotency_key,
                OutcomeEvent.occurred_at,
                OutcomeEvent.created_at,
            )
        )
        row = (await self.conn.execute(stmt)).one()
        return self._row_to_event(row)

    async def get_outcome_event(
        self, *, tenant_id: uuid.UUID, event_id: uuid.UUID
    ) -> OutcomeEventRecord | None:
        stmt = select(OutcomeEvent).where(
            OutcomeEvent.tenant_id == tenant_id,
            OutcomeEvent.id == event_id,
        )
        row = (await self.conn.execute(stmt)).scalars().first()
        if row is None:
            return None
        return OutcomeEventRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            campaign_id=row.campaign_id,
            contact_id=row.contact_id,
            outbound_message_id=row.outbound_message_id,
            event_type=row.event_type,
            note=row.note,
            idempotency_key=row.idempotency_key,
            occurred_at=row.occurred_at,
            created_at=row.created_at,
        )

    async def _get_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, idempotency_key: str
    ) -> OutcomeEventRecord | None:
        stmt = select(OutcomeEvent).where(
            OutcomeEvent.tenant_id == tenant_id,
            OutcomeEvent.idempotency_key == idempotency_key,
        )
        row = (await self.conn.execute(stmt)).scalars().first()
        if row is None:
            return None
        return OutcomeEventRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            campaign_id=row.campaign_id,
            contact_id=row.contact_id,
            outbound_message_id=row.outbound_message_id,
            event_type=row.event_type,
            note=row.note,
            idempotency_key=row.idempotency_key,
            occurred_at=row.occurred_at,
            created_at=row.created_at,
        )

    # ------------------------------------------------------------------
    # ROI Assumptions CRUD
    # ------------------------------------------------------------------

    async def upsert_roi_assumptions(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        cost_per_send_cents: int,
        pipeline_value_per_opportunity_cents: int,
        revenue_per_deal_won_cents: int,
    ) -> ROIAssumptionsRecord:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(CampaignROIAssumptions)
            .values(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                cost_per_send_cents=cost_per_send_cents,
                pipeline_value_per_opportunity_cents=pipeline_value_per_opportunity_cents,
                revenue_per_deal_won_cents=revenue_per_deal_won_cents,
            )
            .on_conflict_do_update(
                index_elements=["campaign_id"],
                set_={
                    "cost_per_send_cents": cost_per_send_cents,
                    "pipeline_value_per_opportunity_cents": pipeline_value_per_opportunity_cents,
                    "revenue_per_deal_won_cents": revenue_per_deal_won_cents,
                    "updated_at": func.now(),
                },
            )
            .returning(
                CampaignROIAssumptions.id,
                CampaignROIAssumptions.tenant_id,
                CampaignROIAssumptions.campaign_id,
                CampaignROIAssumptions.cost_per_send_cents,
                CampaignROIAssumptions.pipeline_value_per_opportunity_cents,
                CampaignROIAssumptions.revenue_per_deal_won_cents,
                CampaignROIAssumptions.created_at,
                CampaignROIAssumptions.updated_at,
            )
        )
        row = (await self.conn.execute(stmt)).one()
        return ROIAssumptionsRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            campaign_id=row.campaign_id,
            cost_per_send_cents=row.cost_per_send_cents,
            pipeline_value_per_opportunity_cents=row.pipeline_value_per_opportunity_cents,
            revenue_per_deal_won_cents=row.revenue_per_deal_won_cents,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_roi_assumptions(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> ROIAssumptionsRecord | None:
        stmt = select(CampaignROIAssumptions).where(
            CampaignROIAssumptions.tenant_id == tenant_id,
            CampaignROIAssumptions.campaign_id == campaign_id,
        )
        row = (await self.conn.execute(stmt)).scalars().first()
        if row is None:
            return None
        return ROIAssumptionsRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            campaign_id=row.campaign_id,
            cost_per_send_cents=row.cost_per_send_cents,
            pipeline_value_per_opportunity_cents=row.pipeline_value_per_opportunity_cents,
            revenue_per_deal_won_cents=row.revenue_per_deal_won_cents,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    async def get_outcome_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> OutcomeTypeCounts:
        """Return per-type counts for outcome events, optionally scoped to
        campaign and date range."""

        from typing import Any

        def _cnt(event_type: str) -> Any:
            return func.count().filter(OutcomeEvent.event_type == event_type)

        stmt = select(
            _cnt("reply_received").label("reply_received"),
            _cnt("positive_reply").label("positive_reply"),
            _cnt("meeting_booked").label("meeting_booked"),
            _cnt("opportunity_created").label("opportunity_created"),
            _cnt("deal_won").label("deal_won"),
            _cnt("deal_lost").label("deal_lost"),
            _cnt("unsubscribed").label("unsubscribed"),
            _cnt("bounced").label("bounced"),
            _cnt("complaint").label("complaint"),
        ).where(OutcomeEvent.tenant_id == tenant_id)

        if campaign_id is not None:
            stmt = stmt.where(OutcomeEvent.campaign_id == campaign_id)
        if date_from is not None:
            stmt = stmt.where(OutcomeEvent.occurred_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(OutcomeEvent.occurred_at <= date_to)

        row = (await self.conn.execute(stmt)).one()
        return OutcomeTypeCounts(
            reply_received=row.reply_received or 0,
            positive_reply=row.positive_reply or 0,
            meeting_booked=row.meeting_booked or 0,
            opportunity_created=row.opportunity_created or 0,
            deal_won=row.deal_won or 0,
            deal_lost=row.deal_lost or 0,
            unsubscribed=row.unsubscribed or 0,
            bounced=row.bounced or 0,
            complaint=row.complaint or 0,
        )

    async def get_outcome_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[OutcomeTrendPoint]:
        """Return daily outcome-event counts bucketed by occurred_at date."""

        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import DATE

        bucket = cast(func.date_trunc("day", OutcomeEvent.occurred_at), DATE).label("bucket_date")
        stmt = (
            select(
                bucket,
                func.count()
                .filter(OutcomeEvent.event_type == "reply_received")
                .label("reply_received"),
                func.count()
                .filter(OutcomeEvent.event_type == "meeting_booked")
                .label("meeting_booked"),
                func.count().filter(OutcomeEvent.event_type == "deal_won").label("deal_won"),
            )
            .where(
                OutcomeEvent.tenant_id == tenant_id,
                OutcomeEvent.occurred_at >= date_from,
                OutcomeEvent.occurred_at <= date_to,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        if campaign_id is not None:
            stmt = stmt.where(OutcomeEvent.campaign_id == campaign_id)

        rows = (await self.conn.execute(stmt)).all()
        return [
            OutcomeTrendPoint(
                bucket_date=r.bucket_date,
                reply_received=r.reply_received or 0,
                meeting_booked=r.meeting_booked or 0,
                deal_won=r.deal_won or 0,
            )
            for r in rows
        ]

    @staticmethod
    def _row_to_event(row: object) -> OutcomeEventRecord:
        return OutcomeEventRecord(
            id=row.id,  # type: ignore[attr-defined]
            tenant_id=row.tenant_id,  # type: ignore[attr-defined]
            campaign_id=row.campaign_id,  # type: ignore[attr-defined]
            contact_id=row.contact_id,  # type: ignore[attr-defined]
            outbound_message_id=row.outbound_message_id,  # type: ignore[attr-defined]
            event_type=row.event_type,  # type: ignore[attr-defined]
            note=row.note,  # type: ignore[attr-defined]
            idempotency_key=row.idempotency_key,  # type: ignore[attr-defined]
            occurred_at=row.occurred_at,  # type: ignore[attr-defined]
            created_at=row.created_at,  # type: ignore[attr-defined]
        )


@dataclass(frozen=True)
class OutcomeTrendPoint:
    bucket_date: object  # datetime.date
    reply_received: int
    meeting_booked: int
    deal_won: int
