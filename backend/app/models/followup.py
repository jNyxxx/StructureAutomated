"""Database models for follow-up rules and schedules (Phase 1 Slice P1-10)."""

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

FOLLOW_UP_SCHEDULE_STATUSES = (
    "scheduled",
    "queued",
    "mock_sent",
    "skipped",
    "canceled",
    "failed",
)
_FOLLOW_UP_SCHEDULE_STATUS_LIST = ",".join(f"'{status}'" for status in FOLLOW_UP_SCHEDULE_STATUSES)


class FollowUpRule(Base):
    """Configuration rule for scheduling automated follow-ups per campaign."""

    __tablename__ = "followup_rules"
    __table_args__ = (
        CheckConstraint(
            "delay_seconds > 0",
            name="ck_followup_rules_delay_seconds",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class FollowUpSchedule(Base):
    """Tracks scheduled follow-up jobs and outcomes."""

    __tablename__ = "followup_schedules"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_FOLLOW_UP_SCHEDULE_STATUS_LIST})",
            name="ck_followup_schedules_status",
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
    original_outbound_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("outbound_messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    original_draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    followup_rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("followup_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="scheduled")
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
