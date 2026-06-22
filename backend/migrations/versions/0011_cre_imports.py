"""CRE contact imports foundation

Revision ID: 00011_cre_imports
Revises: 00010_compliance_suppression
Create Date: 2026-06-23 00:00:11

CSV import/contact persistence only. No later Phase 1 workflows or provider integrations.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00011_cre_imports"
down_revision = "00010_compliance_suppression"
branch_labels = None
depends_on = None

_IMPORT_STATUS_CHECK = "status IN ('pending','processing','completed','failed')"
_IMPORT_ROW_STATUS_CHECK = "status IN ('valid','invalid','duplicate','imported')"


def upgrade() -> None:
    op.create_table(
        "contact_imports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(_IMPORT_STATUS_CHECK, name="ck_contact_imports_status"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_contact_imports_tenant_key"),
    )
    op.create_index("ix_contact_imports_tenant_id", "contact_imports", ["tenant_id"])
    op.create_index("ix_contact_imports_created_by_user_id", "contact_imports", ["created_by_user_id"])

    op.create_table(
        "contacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_import_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contact_imports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dedupe_hash", sa.String(length=64), nullable=False),
        sa.Column("normalized_email", sa.String(length=320), nullable=True),
        sa.Column("normalized_domain", sa.String(length=255), nullable=True),
        sa.Column("normalized_company", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "dedupe_hash", name="uq_contacts_tenant_dedupe_hash"),
    )
    op.create_index("ix_contacts_tenant_id", "contacts", ["tenant_id"])
    op.create_index("ix_contacts_source_import_id", "contacts", ["source_import_id"])

    op.create_table(
        "contact_import_rows",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "import_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contact_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("row_hash", sa.String(length=64), nullable=False),
        sa.Column("dedupe_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("normalized_email", sa.String(length=320), nullable=True),
        sa.Column("normalized_domain", sa.String(length=255), nullable=True),
        sa.Column("normalized_company", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(_IMPORT_ROW_STATUS_CHECK, name="ck_contact_import_rows_status"),
        sa.UniqueConstraint("import_id", "row_number", name="uq_contact_import_rows_import_row"),
    )
    op.create_index("ix_contact_import_rows_tenant_id", "contact_import_rows", ["tenant_id"])
    op.create_index("ix_contact_import_rows_import_id", "contact_import_rows", ["import_id"])
    op.create_index("ix_contact_import_rows_contact_id", "contact_import_rows", ["contact_id"])

    apply_forced_rls("contact_imports")
    apply_forced_rls("contacts")
    apply_forced_rls("contact_import_rows")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS contact_import_rows_tenant_isolation ON contact_import_rows")
    op.execute("DROP POLICY IF EXISTS contacts_tenant_isolation ON contacts")
    op.execute("DROP POLICY IF EXISTS contact_imports_tenant_isolation ON contact_imports")
    op.drop_index("ix_contact_import_rows_contact_id", table_name="contact_import_rows")
    op.drop_index("ix_contact_import_rows_import_id", table_name="contact_import_rows")
    op.drop_index("ix_contact_import_rows_tenant_id", table_name="contact_import_rows")
    op.drop_table("contact_import_rows")
    op.drop_index("ix_contacts_source_import_id", table_name="contacts")
    op.drop_index("ix_contacts_tenant_id", table_name="contacts")
    op.drop_table("contacts")
    op.drop_index("ix_contact_imports_created_by_user_id", table_name="contact_imports")
    op.drop_index("ix_contact_imports_tenant_id", table_name="contact_imports")
    op.drop_table("contact_imports")
