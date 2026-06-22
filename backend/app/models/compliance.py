"""Compliance profile and suppression baseline models.

US-first cold outreach compliance baseline only. No real sending, SMS provider,
webhooks, or Phase 1 outreach flow is implemented here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CHANNELS = ("email", "sms")
_CHANNEL_LIST = ",".join(f"'{channel}'" for channel in CHANNELS)


class ComplianceProfile(Base):
    __tablename__ = "compliance_profiles"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_compliance_profiles_tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, server_default="US")
    sending_review_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    live_sending_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    sms_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Suppression(Base):
    __tablename__ = "suppressions"
    __table_args__ = (
        CheckConstraint(f"channel IN ({_CHANNEL_LIST})", name="ck_suppressions_channel"),
        UniqueConstraint(
            "tenant_id", "channel", "contact_hash", name="uq_suppressions_tenant_channel_hash"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    contact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    never_contact: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
