"""add drafts and draft evidence

Revision ID: 00015_drafts
Revises: 00014_knowledge
Create Date: 2026-06-23 00:00:15

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00015_drafts"
down_revision = "00014_knowledge"
branch_labels = None
depends_on = None

_DRAFT_STATUS_CHECK = "status IN ('generated','blocked','needs_regeneration','archived')"
_DRAFT_EVIDENCE_SOURCE_TYPE_CHECK = "source_type IN ('knowledge_chunk','research_artifact')"


def upgrade() -> None:
    # 1. Create drafts table
    op.create_table(
        "drafts",
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
        sa.Column("status", sa.Text(), nullable=False, server_default="generated"),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
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
        sa.CheckConstraint(_DRAFT_STATUS_CHECK, name="ck_drafts_status"),
    )
    op.create_index("ix_drafts_tenant_id", "drafts", ["tenant_id"])
    op.create_index("ix_drafts_campaign_id", "drafts", ["campaign_id"])
    op.create_index("ix_drafts_contact_id", "drafts", ["contact_id"])

    # 2. Create draft_evidence table
    op.create_table(
        "draft_evidence",
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
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_snippet", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(_DRAFT_EVIDENCE_SOURCE_TYPE_CHECK, name="ck_draft_evidence_source_type"),
    )
    op.create_index("ix_draft_evidence_tenant_id", "draft_evidence", ["tenant_id"])
    op.create_index("ix_draft_evidence_draft_id", "draft_evidence", ["draft_id"])

    # 3. Apply Forced RLS and tenant isolation policies
    apply_forced_rls("drafts")
    apply_forced_rls("draft_evidence")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS draft_evidence_tenant_isolation ON draft_evidence")
    op.execute("DROP POLICY IF EXISTS drafts_tenant_isolation ON drafts")
    op.drop_index("ix_draft_evidence_draft_id", table_name="draft_evidence")
    op.drop_index("ix_draft_evidence_tenant_id", table_name="draft_evidence")
    op.drop_table("draft_evidence")
    op.drop_index("ix_drafts_contact_id", table_name="drafts")
    op.drop_index("ix_drafts_campaign_id", table_name="drafts")
    op.drop_index("ix_drafts_tenant_id", table_name="drafts")
    op.drop_table("drafts")
