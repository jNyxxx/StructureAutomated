"""Alembic migration: add outcome_events and campaign_roi_assumptions tables.

Revision ID: 00021_outcomes
Revises: 00020_followups
Create Date: 2026-06-23 00:00:21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "00021_outcomes"
down_revision = "00020_followups"
branch_labels = None
depends_on = None

_OUTCOME_EVENT_TYPES = (
    "reply_received",
    "positive_reply",
    "meeting_booked",
    "opportunity_created",
    "deal_won",
    "deal_lost",
    "unsubscribed",
    "bounced",
    "complaint",
)
_OUTCOME_TYPES_CHECK = "event_type IN ({})".format(
    ", ".join(f"'{t}'" for t in _OUTCOME_EVENT_TYPES)
)


def upgrade() -> None:
    # 1. outcome_events -------------------------------------------------------
    op.create_table(
        "outcome_events",
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
            "outbound_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("outbound_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True, unique=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(_OUTCOME_TYPES_CHECK, name="ck_outcome_events_event_type"),
    )
    op.create_index("ix_outcome_events_tenant_id", "outcome_events", ["tenant_id"])
    op.create_index("ix_outcome_events_campaign_id", "outcome_events", ["campaign_id"])
    op.create_index("ix_outcome_events_contact_id", "outcome_events", ["contact_id"])
    op.create_index(
        "ix_outcome_events_outbound_message_id", "outcome_events", ["outbound_message_id"]
    )
    op.create_index("ix_outcome_events_event_type", "outcome_events", ["event_type"])
    op.create_index("ix_outcome_events_occurred_at", "outcome_events", ["occurred_at"])

    apply_forced_rls("outcome_events")

    # 2. campaign_roi_assumptions ----------------------------------------------
    op.create_table(
        "campaign_roi_assumptions",
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
        sa.Column("cost_per_send_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "pipeline_value_per_opportunity_cents",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "revenue_per_deal_won_cents", sa.Integer(), nullable=False, server_default="0"
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
    )
    op.create_index(
        "ix_campaign_roi_assumptions_tenant_id", "campaign_roi_assumptions", ["tenant_id"]
    )
    op.create_index(
        "ix_campaign_roi_assumptions_campaign_id", "campaign_roi_assumptions", ["campaign_id"]
    )

    apply_forced_rls("campaign_roi_assumptions")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS campaign_roi_assumptions_tenant_isolation "
        "ON campaign_roi_assumptions"
    )
    op.execute(
        "DROP POLICY IF EXISTS outcome_events_tenant_isolation ON outcome_events"
    )
    op.drop_index("ix_campaign_roi_assumptions_campaign_id", table_name="campaign_roi_assumptions")
    op.drop_index("ix_campaign_roi_assumptions_tenant_id", table_name="campaign_roi_assumptions")
    op.drop_table("campaign_roi_assumptions")

    op.drop_index("ix_outcome_events_occurred_at", table_name="outcome_events")
    op.drop_index("ix_outcome_events_event_type", table_name="outcome_events")
    op.drop_index("ix_outcome_events_outbound_message_id", table_name="outcome_events")
    op.drop_index("ix_outcome_events_contact_id", table_name="outcome_events")
    op.drop_index("ix_outcome_events_campaign_id", table_name="outcome_events")
    op.drop_index("ix_outcome_events_tenant_id", table_name="outcome_events")
    op.drop_table("outcome_events")
