"""ORM models for campaign outcome events and ROI assumptions (Phase 1 Slice P1-12).

outcome_events — one row per observable outcome for a (tenant, campaign, contact) triple.
campaign_roi_assumptions — per-campaign cost/value assumptions for ROI calculation.

Both tables carry forced RLS; all queries require the tenant DB context to be set.
No real CRM, payment, or ad-platform connectors are implemented here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# ---------------------------------------------------------------------------
# Allowed outcome event types
# ---------------------------------------------------------------------------

OUTCOME_EVENT_TYPES = (
    "reply_received",
    "positive_reply",
    "meeting_booked",
    "opportunity_created",
    "deal_won",
    "deal_lost",
    "unsubscribed",
    "bounced",
    "complaint",
)
_OUTCOME_TYPES_LIST = ",".join(f"'{t}'" for t in OUTCOME_EVENT_TYPES)


class OutcomeEvent(Base):
    """A single observable outcome event for a contact in a campaign.

    Recorded deterministically from mock send data or manually in tests.
    No real CRM / payment connector is used.
    """

    __tablename__ = "outcome_events"
    __table_args__ = (
        CheckConstraint(
            f"event_type IN ({_OUTCOME_TYPES_LIST})",
            name="ck_outcome_events_event_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # outbound_message_id is optional: events not tied to a specific send (e.g.
    # manually recorded meetings) may omit it.
    outbound_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("outbound_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    # Optional free-text note kept minimal (no raw contact data / secrets).
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Idempotency key: callers may supply a stable key to prevent duplicate events.
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CampaignROIAssumptions(Base):
    """Per-campaign cost/value assumptions for deterministic ROI calculation.

    Values are set by the tenant owner and used only for mock ROI math.
    No real payment or revenue data is stored here.
    """

    __tablename__ = "campaign_roi_assumptions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # One row per campaign; unique enforced.
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Cost per sent email in cents (integer, avoids float rounding).
    cost_per_send_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Estimated pipeline value per opportunity created, in cents.
    pipeline_value_per_opportunity_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    # Estimated revenue per deal won, in cents.
    revenue_per_deal_won_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
