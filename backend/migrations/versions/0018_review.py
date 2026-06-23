"""add review items table

Revision ID: 00018_review
Revises: 00017_groundedness
Create Date: 2026-06-23 00:00:18

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00018_review"
down_revision = "00017_groundedness"
branch_labels = None
depends_on = None

_REVIEW_STATUS_CHECK = "status IN ('pending_review', 'approved', 'rejected', 'regeneration_requested')"


def upgrade() -> None:
    op.create_table(
        "review_items",
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
        sa.Column("status", sa.Text(), nullable=False, server_default="pending_review"),
        sa.Column(
            "reviewer_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action_reason", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_at",
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
        sa.CheckConstraint(_REVIEW_STATUS_CHECK, name="ck_review_items_status"),
    )
    op.create_index("ix_review_items_tenant_id", "review_items", ["tenant_id"])
    op.create_index("ix_review_items_draft_id", "review_items", ["draft_id"])
    op.create_index("ix_review_items_campaign_id", "review_items", ["campaign_id"])
    op.create_index("ix_review_items_status", "review_items", ["status"])

    apply_forced_rls("review_items")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS review_items_tenant_isolation ON review_items")
    op.drop_index("ix_review_items_status", table_name="review_items")
    op.drop_index("ix_review_items_campaign_id", table_name="review_items")
    op.drop_index("ix_review_items_draft_id", table_name="review_items")
    op.drop_index("ix_review_items_tenant_id", table_name="review_items")
    op.drop_table("review_items")
