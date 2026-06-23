"""Draft and draft evidence models for Phase 1 Slice P1-05."""

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

DRAFT_STATUSES = ("generated", "blocked", "needs_regeneration", "archived")
_DRAFT_STATUS_LIST = ",".join(f"'{status}'" for status in DRAFT_STATUSES)

DRAFT_EVIDENCE_SOURCES = ("knowledge_chunk", "research_artifact")
_DRAFT_EVIDENCE_SOURCES_LIST = ",".join(f"'{src}'" for src in DRAFT_EVIDENCE_SOURCES)


class Draft(Base):
    """Draft message for a campaign contact."""

    __tablename__ = "drafts"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_DRAFT_STATUS_LIST})",
            name="ck_drafts_status",
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
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'generated'"))
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class DraftEvidence(Base):
    """Evidence linking a draft to its grounding context or research artifact sources."""

    __tablename__ = "draft_evidence"
    __table_args__ = (
        CheckConstraint(
            f"source_type IN ({_DRAFT_EVIDENCE_SOURCES_LIST})",
            name="ck_draft_evidence_source_type",
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
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    content_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
