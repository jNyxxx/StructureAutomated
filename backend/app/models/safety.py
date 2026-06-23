"""Safety gate evaluation models for Phase 1 Slice P1-06."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

SAFETY_GATES = ("prompt_injection", "source_trust")
_SAFETY_GATE_LIST = ",".join(f"'{gate}'" for gate in SAFETY_GATES)

SAFETY_STATUSES = ("passed", "warning", "failed")
_SAFETY_STATUS_LIST = ",".join(f"'{status}'" for status in SAFETY_STATUSES)

SAFETY_SEVERITIES = ("info", "low", "medium", "high", "critical")
_SAFETY_SEVERITY_LIST = ",".join(f"'{sev}'" for sev in SAFETY_SEVERITIES)


class SafetyGateResult(Base):
    """Evaluation result for a safety gate check (e.g. prompt injection, source trust)."""

    __tablename__ = "safety_gate_results"
    __table_args__ = (
        CheckConstraint(
            f"gate_type IN ({_SAFETY_GATE_LIST})",
            name="ck_safety_gate_results_gate_type",
        ),
        CheckConstraint(
            f"status IN ({_SAFETY_STATUS_LIST})",
            name="ck_safety_gate_results_status",
        ),
        CheckConstraint(
            f"severity IN ({_SAFETY_SEVERITY_LIST})",
            name="ck_safety_gate_results_severity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    gate_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'info'"))
    reason_code: Mapped[str] = mapped_column(Text, nullable=False)
    safe_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
