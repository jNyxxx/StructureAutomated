"""add followup rules and schedules tables

Revision ID: 00020_followups
Revises: 00019_mock_sending
Create Date: 2026-06-23 00:00:20

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00020_followups"
down_revision = "00019_mock_sending"
branch_labels = None
depends_on = None

_FOLLOW_UP_SCHEDULE_STATUS_CHECK = (
    "status IN ('scheduled', 'queued', 'mock_sent', 'skipped', 'canceled', 'failed')"
)


def upgrade() -> None:
    # 1. Create followup_rules table
    op.create_table(
        "followup_rules",
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
            unique=True,
        ),
        sa.Column("delay_seconds", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("delay_seconds > 0", name="ck_followup_rules_delay_seconds"),
    )
    op.create_index("ix_followup_rules_tenant_id", "followup_rules", ["tenant_id"])
    op.create_index("ix_followup_rules_campaign_id", "followup_rules", ["campaign_id"])

    # 2. Create followup_schedules table
    op.create_table(
        "followup_schedules",
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
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "original_outbound_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("outbound_messages.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "original_draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "followup_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("followup_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="scheduled"),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_role", sa.Text(), nullable=False),
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
        sa.CheckConstraint(_FOLLOW_UP_SCHEDULE_STATUS_CHECK, name="ck_followup_schedules_status"),
    )
    op.create_index("ix_followup_schedules_tenant_id", "followup_schedules", ["tenant_id"])
    op.create_index("ix_followup_schedules_campaign_id", "followup_schedules", ["campaign_id"])
    op.create_index("ix_followup_schedules_contact_id", "followup_schedules", ["contact_id"])
    op.create_index(
        "ix_followup_schedules_original_outbound_message_id",
        "followup_schedules",
        ["original_outbound_message_id"],
    )
    op.create_index("ix_followup_schedules_original_draft_id", "followup_schedules", ["original_draft_id"])
    op.create_index("ix_followup_schedules_followup_rule_id", "followup_schedules", ["followup_rule_id"])

    # Apply forced RLS
    apply_forced_rls("followup_rules")
    apply_forced_rls("followup_schedules")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS followup_schedules_tenant_isolation ON followup_schedules")
    op.execute("DROP POLICY IF EXISTS followup_rules_tenant_isolation ON followup_rules")

    op.drop_index("ix_followup_schedules_followup_rule_id", table_name="followup_schedules")
    op.drop_index("ix_followup_schedules_original_draft_id", table_name="followup_schedules")
    op.drop_index("ix_followup_schedules_original_outbound_message_id", table_name="followup_schedules")
    op.drop_index("ix_followup_schedules_contact_id", table_name="followup_schedules")
    op.drop_index("ix_followup_schedules_campaign_id", table_name="followup_schedules")
    op.drop_index("ix_followup_schedules_tenant_id", table_name="followup_schedules")
    op.drop_table("followup_schedules")

    op.drop_index("ix_followup_rules_campaign_id", table_name="followup_rules")
    op.drop_index("ix_followup_rules_tenant_id", table_name="followup_rules")
    op.drop_table("followup_rules")
