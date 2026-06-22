"""compliance profiles and suppression baseline

Revision ID: 00010_compliance_suppression
Revises: 0009_mock_billing
Create Date: 2026-06-22 00:00:09

US-first compliance baseline for cold outreach assumptions only. No real sending,
SMS provider integration, frontend, or Phase 1 outreach flow.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "00010_compliance_suppression"
down_revision = "0009_mock_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_profiles",
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
        sa.Column("jurisdiction", sa.String(length=50), nullable=False, server_default="US"),
        sa.Column("sending_review_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("live_sending_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sms_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", name="uq_compliance_profiles_tenant_id"),
    )
    op.create_index("ix_compliance_profiles_tenant_id", "compliance_profiles", ["tenant_id"])

    op.create_table(
        "suppressions",
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
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("contact_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("never_contact", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("channel IN ('email','sms')", name="ck_suppressions_channel"),
        sa.UniqueConstraint(
            "tenant_id", "channel", "contact_hash", name="uq_suppressions_tenant_channel_hash"
        ),
    )
    op.create_index("ix_suppressions_tenant_id", "suppressions", ["tenant_id"])
    op.create_index("ix_suppressions_lookup", "suppressions", ["tenant_id", "channel", "contact_hash"])

    op.execute("ALTER TABLE compliance_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE compliance_profiles FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY compliance_profiles_tenant_isolation ON compliance_profiles "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"
    )
    op.execute("ALTER TABLE suppressions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE suppressions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY suppressions_tenant_isolation ON suppressions "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS suppressions_tenant_isolation ON suppressions")
    op.execute("DROP POLICY IF EXISTS compliance_profiles_tenant_isolation ON compliance_profiles")
    op.drop_index("ix_suppressions_lookup", table_name="suppressions")
    op.drop_index("ix_suppressions_tenant_id", table_name="suppressions")
    op.drop_table("suppressions")
    op.drop_index("ix_compliance_profiles_tenant_id", table_name="compliance_profiles")
    op.drop_table("compliance_profiles")
