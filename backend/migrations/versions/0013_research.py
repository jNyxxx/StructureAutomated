"""add research runs and artifacts tables

Revision ID: 0013_research
Revises: 0012_campaigns
Create Date: 2026-06-23 00:00:13

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00013_research"
down_revision = "00012_campaigns"
branch_labels = None
depends_on = None

_RESEARCH_RUN_STATUS_CHECK = "status IN ('pending','running','completed','failed')"


def upgrade() -> None:
    op.create_table(
        "research_runs",
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
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("queued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(_RESEARCH_RUN_STATUS_CHECK, name="ck_research_runs_status"),
    )
    op.create_index("ix_research_runs_tenant_id", "research_runs", ["tenant_id"])
    op.create_index("ix_research_runs_campaign_id", "research_runs", ["campaign_id"])
    op.create_index("ix_research_runs_created_by_user_id", "research_runs", ["created_by_user_id"])

    op.create_table(
        "research_artifacts",
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
            "research_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_research_artifacts_tenant_id", "research_artifacts", ["tenant_id"])
    op.create_index("ix_research_artifacts_research_run_id", "research_artifacts", ["research_run_id"])
    op.create_index("ix_research_artifacts_contact_id", "research_artifacts", ["contact_id"])

    apply_forced_rls("research_runs")
    apply_forced_rls("research_artifacts")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS research_artifacts_tenant_isolation ON research_artifacts")
    op.execute("DROP POLICY IF EXISTS research_runs_tenant_isolation ON research_runs")
    op.drop_index("ix_research_artifacts_contact_id", table_name="research_artifacts")
    op.drop_index("ix_research_artifacts_research_run_id", table_name="research_artifacts")
    op.drop_index("ix_research_artifacts_tenant_id", table_name="research_artifacts")
    op.drop_table("research_artifacts")
    op.drop_index("ix_research_runs_created_by_user_id", table_name="research_runs")
    op.drop_index("ix_research_runs_campaign_id", table_name="research_runs")
    op.drop_index("ix_research_runs_tenant_id", table_name="research_runs")
    op.drop_table("research_runs")
