"""Mock MVP billing models.

Local MVP billing is deterministic schema + access gates only. No real Stripe
checkout, API calls, webhooks, money movement, provider objects, or secrets.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

BILLING_STATES = ("trialing", "active", "past_due", "canceled", "unpaid", "inactive")
_BILLING_STATE_LIST = ",".join(f"'{state}'" for state in BILLING_STATES)


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("key", name="uq_plans_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    features: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"
    __table_args__ = (
        CheckConstraint(
            f"tenant_status IN ({_BILLING_STATE_LIST})",
            name="ck_tenant_subscriptions_status",
        ),
        UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tenant_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="inactive")
    grace_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
