"""campaign creation and contact selection foundation

Revision ID: 00012_campaigns
Revises: 00011_cre_imports
Create Date: 2026-06-23 00:00:12

Campaign metadata and contact selection only. No later Phase 1 workflow stages or
provider integrations.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00012_campaigns"
down_revision = "00011_cre_imports"
branch_labels = None
depends_on = None

_CAMPAIGN_STATUS_CHECK = "status IN ('draft','ready','paused','archived')"
_CAMPAIGN_CONTACT_STATUS_CHECK = "status IN ('selected','excluded','queued_for_research')"


def upgrade() -> None:
    op.create_table(
        "campaigns",
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
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("target_segment", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(_CAMPAIGN_STATUS_CHECK, name="ck_campaigns_status"),
    )
    op.create_index("ix_campaigns_tenant_id", "campaigns", ["tenant_id"])
    op.create_index("ix_campaigns_created_by_user_id", "campaigns", ["created_by_user_id"])

    op.create_table(
        "campaign_contacts",
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
        sa.Column("status", sa.Text(), nullable=False, server_default="selected"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(_CAMPAIGN_CONTACT_STATUS_CHECK, name="ck_campaign_contacts_status"),
        sa.UniqueConstraint("campaign_id", "contact_id", name="uq_campaign_contacts_campaign_contact"),
    )
    op.create_index("ix_campaign_contacts_tenant_id", "campaign_contacts", ["tenant_id"])
    op.create_index("ix_campaign_contacts_campaign_id", "campaign_contacts", ["campaign_id"])
    op.create_index("ix_campaign_contacts_contact_id", "campaign_contacts", ["contact_id"])

    apply_forced_rls("campaigns")
    apply_forced_rls("campaign_contacts")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS campaign_contacts_tenant_isolation ON campaign_contacts")
    op.execute("DROP POLICY IF EXISTS campaigns_tenant_isolation ON campaigns")
    op.drop_index("ix_campaign_contacts_contact_id", table_name="campaign_contacts")
    op.drop_index("ix_campaign_contacts_campaign_id", table_name="campaign_contacts")
    op.drop_index("ix_campaign_contacts_tenant_id", table_name="campaign_contacts")
    op.drop_table("campaign_contacts")
    op.drop_index("ix_campaigns_created_by_user_id", table_name="campaigns")
    op.drop_index("ix_campaigns_tenant_id", table_name="campaigns")
    op.drop_table("campaigns")
