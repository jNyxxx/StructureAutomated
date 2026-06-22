"""integration_credentials: tenant secret references (ref + metadata only) + forced RLS

Revision ID: 0004_integration_credentials
Revises: 0003_audit_events
Create Date: 2026-06-22 00:00:03

Stores only secret_ref + envelope metadata — never plaintext or ciphertext.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "0004_integration_credentials"
down_revision = "0003_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_credentials",
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
        sa.Column("credential_type", sa.String(100), nullable=False),
        sa.Column("secret_ref", sa.Text, nullable=False),
        sa.Column("envelope_key_id", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotation_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "tenant_id", "credential_type", name="uq_integration_credentials_tenant_type"
        ),
    )
    op.create_index(
        "ix_integration_credentials_tenant_id", "integration_credentials", ["tenant_id"]
    )
    apply_forced_rls("integration_credentials")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS integration_credentials_tenant_isolation "
        "ON integration_credentials"
    )
    op.drop_index("ix_integration_credentials_tenant_id", table_name="integration_credentials")
    op.drop_table("integration_credentials")
