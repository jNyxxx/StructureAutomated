"""Job — durable queue/outbox row. Postgres is the source of truth.

Tenant-owned (``tenant_id`` NOT NULL) with forced RLS. The worker claims across
tenants via an explicit worker-context clause in the RLS policy (migration 0006),
then processes each job under its own tenant context. Stores only a safe
``last_error`` (exception type — never raw error text or secrets) and a payload
that callers must keep free of secrets (CLAUDE.md rule 14).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class JobStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELED = "canceled"


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_jobs_tenant_idempotency_key"),
        CheckConstraint(
            "status IN ('queued', 'leased', 'running', 'succeeded', "
            "'failed', 'dead_letter', 'canceled')",
            name="ck_jobs_status",
        ),
        Index("ix_jobs_status_run_after", "status", "run_after"),
        Index("ix_jobs_tenant_status_run_after", "tenant_id", "status", "run_after"),
        Index("ix_jobs_locked_until", "locked_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'queued'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
