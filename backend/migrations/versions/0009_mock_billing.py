"""mock billing schema: plans, tenant subscriptions, central gate data

Revision ID: 0009_mock_billing
Revises: 0008_support_access_grants
Create Date: 2026-06-22 00:00:08

Local/mock MVP billing only. No real checkout, API calls, provider objects,
credentials, or money movement.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_mock_billing"
down_revision = "0008_support_access_grants"
branch_labels = None
depends_on = None

_STATE_CHECK = "tenant_status IN ('trialing','active','past_due','canceled','unpaid','inactive')"
_FEATURES = (
    '{"can_send": true, "can_run_agents": true, '
    '"can_create_campaign": true, "can_export": true}'
)


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("key", name="uq_plans_key"),
    )

    op.create_table(
        "tenant_subscriptions",
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
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tenant_status", sa.Text(), nullable=False, server_default="inactive"),
        sa.Column("grace_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(_STATE_CHECK, name="ck_tenant_subscriptions_status"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant_id"),
    )
    op.create_index("ix_tenant_subscriptions_tenant_id", "tenant_subscriptions", ["tenant_id"])
    op.create_index("ix_tenant_subscriptions_plan_id", "tenant_subscriptions", ["plan_id"])

    op.execute("ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_subscriptions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_subscriptions_tenant_isolation ON tenant_subscriptions "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"
    )

    op.execute(
        "INSERT INTO plans (key, name, features) VALUES "
        f"('mvp_mock', 'MVP Mock Plan', '{_FEATURES}'::jsonb)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_subscriptions_tenant_isolation ON tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_plan_id", table_name="tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_tenant_id", table_name="tenant_subscriptions")
    op.drop_table("tenant_subscriptions")
    op.drop_table("plans")
