"""add safety gate results

Revision ID: 00016_safety
Revises: 00015_drafts
Create Date: 2026-06-23 00:00:16

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00016_safety"
down_revision = "00015_drafts"
branch_labels = None
depends_on = None

_SAFETY_GATE_CHECK = "gate_type IN ('prompt_injection','source_trust')"
_SAFETY_STATUS_CHECK = "status IN ('passed','warning','failed')"
_SAFETY_SEVERITY_CHECK = "severity IN ('info','low','medium','high','critical')"


def upgrade() -> None:
    op.create_table(
        "safety_gate_results",
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
            nullable=True,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drafts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("gate_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False, server_default="info"),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column(
            "safe_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(_SAFETY_GATE_CHECK, name="ck_safety_gate_results_gate_type"),
        sa.CheckConstraint(_SAFETY_STATUS_CHECK, name="ck_safety_gate_results_status"),
        sa.CheckConstraint(_SAFETY_SEVERITY_CHECK, name="ck_safety_gate_results_severity"),
    )
    op.create_index("ix_safety_gate_results_tenant_id", "safety_gate_results", ["tenant_id"])
    op.create_index("ix_safety_gate_results_campaign_id", "safety_gate_results", ["campaign_id"])
    op.create_index("ix_safety_gate_results_contact_id", "safety_gate_results", ["contact_id"])
    op.create_index("ix_safety_gate_results_gate_type", "safety_gate_results", ["gate_type"])

    apply_forced_rls("safety_gate_results")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS safety_gate_results_tenant_isolation ON safety_gate_results")
    op.drop_index("ix_safety_gate_results_gate_type", table_name="safety_gate_results")
    op.drop_index("ix_safety_gate_results_contact_id", table_name="safety_gate_results")
    op.drop_index("ix_safety_gate_results_campaign_id", table_name="safety_gate_results")
    op.drop_index("ix_safety_gate_results_tenant_id", table_name="safety_gate_results")
    op.drop_table("safety_gate_results")
