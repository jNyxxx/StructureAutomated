"""CRE contact and CSV import models for Phase 1 Slice P1-01.

This slice implements import/storage only. It does not create campaigns, research,
RAG, draft generation, review, sending, follow-ups, or dashboards.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

IMPORT_STATUSES = ("pending", "processing", "completed", "failed")
IMPORT_ROW_STATUSES = ("valid", "invalid", "duplicate", "imported")
_IMPORT_STATUS_LIST = ",".join(f"'{status}'" for status in IMPORT_STATUSES)
_IMPORT_ROW_STATUS_LIST = ",".join(f"'{status}'" for status in IMPORT_ROW_STATUSES)


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dedupe_hash", name="uq_contacts_tenant_dedupe_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_import_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("contact_imports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dedupe_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    normalized_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ContactImport(Base):
    __tablename__ = "contact_imports"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_IMPORT_STATUS_LIST})",
            name="ck_contact_imports_status",
        ),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_contact_imports_tenant_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContactImportRow(Base):
    __tablename__ = "contact_import_rows"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_IMPORT_ROW_STATUS_LIST})",
            name="ck_contact_import_rows_status",
        ),
        UniqueConstraint("import_id", "row_number", name="uq_contact_import_rows_import_row"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contact_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    validation_errors: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    normalized_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    normalized_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
