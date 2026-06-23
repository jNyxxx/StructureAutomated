"""add mock sending tables

Revision ID: 00019_mock_sending
Revises: 00018_review
Create Date: 2026-06-23 00:00:19

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00019_mock_sending"
down_revision = "00018_review"
branch_labels = None
depends_on = None

_SEND_GATE_STATUS_CHECK = "status IN ('passed', 'denied')"
_DENY_REASON_CODES_CHECK = (
    "deny_reason_code IS NULL OR deny_reason_code IN ("
    "'draft_not_approved', 'review_not_approved', 'contact_suppressed', "
    "'billing_blocked', 'permission_denied', 'safety_missing', 'safety_failed', "
    "'groundedness_missing', 'groundedness_failed', 'invalid_draft_state', "
    "'duplicate_send', 'tenant_mismatch', 'throttled')"
)
_OUTBOUND_STATUS_CHECK = "status IN ('mock_queued', 'mock_sent', 'blocked', 'duplicate')"


def upgrade() -> None:
    # 1. Create send_gate_results table
    op.create_table(
        "send_gate_results",
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
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("deny_reason_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(_SEND_GATE_STATUS_CHECK, name="ck_send_gate_results_status"),
        sa.CheckConstraint(_DENY_REASON_CODES_CHECK, name="ck_send_gate_results_deny_reason_code"),
    )
    op.create_index("ix_send_gate_results_tenant_id", "send_gate_results", ["tenant_id"])
    op.create_index("ix_send_gate_results_draft_id", "send_gate_results", ["draft_id"])

    # 2. Create outbound_messages table
    op.create_table(
        "outbound_messages",
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
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drafts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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
        sa.CheckConstraint(_OUTBOUND_STATUS_CHECK, name="ck_outbound_messages_status"),
    )
    op.create_index("ix_outbound_messages_tenant_id", "outbound_messages", ["tenant_id"])
    op.create_index("ix_outbound_messages_draft_id", "outbound_messages", ["draft_id"])

    # Apply forced RLS
    apply_forced_rls("send_gate_results")
    apply_forced_rls("outbound_messages")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS outbound_messages_tenant_isolation ON outbound_messages")
    op.execute("DROP POLICY IF EXISTS send_gate_results_tenant_isolation ON send_gate_results")

    op.drop_index("ix_outbound_messages_draft_id", table_name="outbound_messages")
    op.drop_index("ix_outbound_messages_tenant_id", table_name="outbound_messages")
    op.drop_table("outbound_messages")

    op.drop_index("ix_send_gate_results_draft_id", table_name="send_gate_results")
    op.drop_index("ix_send_gate_results_tenant_id", table_name="send_gate_results")
    op.drop_table("send_gate_results")
