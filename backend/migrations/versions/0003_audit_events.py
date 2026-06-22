"""audit_events: append-only audit trail (grants + immutability trigger)

Revision ID: 0003_audit_events
Revises: 0002_core_tenancy
Create Date: 2026-06-22 00:00:02

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_audit_events"
down_revision = "0002_core_tenancy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("object_type", sa.Text, nullable=True),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.Text, nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "redacted_details",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "CREATE INDEX ix_audit_events_tenant_created_at "
        "ON audit_events (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_audit_events_object ON audit_events (tenant_id, object_type, object_id)"
    )

    # Append-only: block UPDATE/DELETE for everyone (including the table owner).
    op.execute(
        "CREATE OR REPLACE FUNCTION audit_events_block_mutation() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN "
        "RAISE EXCEPTION 'audit_events is append-only'; END; $$"
    )
    op.execute(
        "CREATE TRIGGER audit_events_no_mutation BEFORE UPDATE OR DELETE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION audit_events_block_mutation()"
    )

    # App role: INSERT/SELECT only. Applied only if the role exists in this env.
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_role') THEN "
        "GRANT INSERT, SELECT ON audit_events TO app_role; "
        "REVOKE UPDATE, DELETE ON audit_events FROM app_role; END IF; END $$"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_mutation ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_block_mutation()")
    op.drop_table("audit_events")
