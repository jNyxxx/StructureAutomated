"""IdempotencyKey — retry-safe replay record for risky actions.

Cross-cutting infra table with a nullable ``tenant_id`` (webhook/system keys
carry no tenant). Forced RLS isolates tenant rows to their own tenant context;
NULL-tenant rows are reachable only when no tenant context is set (system/worker
path), never by a tenant request. Uniqueness uses two partial unique indexes so
a NULL-tenant key cannot be duplicated. The forced-RLS policy + index DDL live
in migration ``0005_idempotency_keys``.

Stores only hashes of the request/response — never the raw payloads
(CLAUDE.md rule 14).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        # Nullable tenant_id: partial unique indexes so NULL-tenant (system) keys
        # are unique on (key) alone — a plain UNIQUE would treat NULLs as distinct
        # and allow duplicate system keys.
        Index(
            "uq_idempotency_keys_tenant_key",
            "tenant_id",
            "key",
            unique=True,
            postgresql_where=text("tenant_id IS NOT NULL"),
        ),
        Index(
            "uq_idempotency_keys_system_key",
            "key",
            unique=True,
            postgresql_where=text("tenant_id IS NULL"),
        ),
        Index("ix_idempotency_keys_expiry", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE")
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(Text, nullable=False)
    request_hash: Mapped[str] = mapped_column(Text, nullable=False)
    response_hash: Mapped[str | None] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(Integer)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
