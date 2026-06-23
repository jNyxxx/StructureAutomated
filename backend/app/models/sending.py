"""Database models for mock sending and evaluation gates (Phase 1 Slice P1-09)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

SEND_GATE_STATUSES = ("passed", "denied")
_SEND_GATE_STATUS_LIST = ",".join(f"'{status}'" for status in SEND_GATE_STATUSES)

DENY_REASON_CODES = (
    "draft_not_approved",
    "review_not_approved",
    "contact_suppressed",
    "billing_blocked",
    "permission_denied",
    "safety_missing",
    "safety_failed",
    "groundedness_missing",
    "groundedness_failed",
    "invalid_draft_state",
    "duplicate_send",
    "tenant_mismatch",
    "throttled",
)
_DENY_REASON_CODES_LIST = ",".join(f"'{code}'" for code in DENY_REASON_CODES)

OUTBOUND_MESSAGE_STATUSES = ("mock_queued", "mock_sent", "blocked", "duplicate")
_OUTBOUND_STATUS_LIST = ",".join(f"'{status}'" for status in OUTBOUND_MESSAGE_STATUSES)


class SendGateResult(Base):
    """Result of send gate evaluations before sending outbound messages."""

    __tablename__ = "send_gate_results"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_SEND_GATE_STATUS_LIST})",
            name="ck_send_gate_results_status",
        ),
        CheckConstraint(
            f"deny_reason_code IS NULL OR deny_reason_code IN ({_DENY_REASON_CODES_LIST})",
            name="ck_send_gate_results_deny_reason_code",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    deny_reason_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class OutboundMessage(Base):
    """Outbound email sent through the mock sender."""

    __tablename__ = "outbound_messages"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_OUTBOUND_STATUS_LIST})",
            name="ck_outbound_messages_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
