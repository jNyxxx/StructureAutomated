"""audit_events: append-only audit trail (forced RLS + grants + immutability trigger)

Revision ID: 0003_audit_events
Revises: 0002_core_tenancy
Create Date: 2026-06-22 00:00:02

tenant_id is nullable (platform/system events carry no tenant). Forced RLS with a
NULL-aware policy (same shape as idempotency_keys) isolates tenant rows to their
own tenant context; platform/system (NULL-tenant) rows are reachable ONLY when no
tenant context is set (system path) — never by a tenant request. This is in
addition to the append-only trigger (blocks UPDATE/DELETE) and least-privilege
grants. Audit isolation is strictly tenant / NULL-aware: unlike jobs, there is no
worker-context read bypass.
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

    # Forced RLS with NULL-aware tenant isolation (mirrors idempotency_keys).
    # Tenant rows match the current tenant context; platform/system (NULL-tenant)
    # rows are visible ONLY when no tenant context is set. Identical USING +
    # WITH CHECK so a tenant request can neither read nor write system rows, and
    # vice versa. Static literal — no interpolation; table/columns are
    # developer-controlled.
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY audit_events_tenant_isolation ON audit_events USING ("
        "tenant_id = current_setting('app.current_tenant_id', true)::uuid "
        "OR (tenant_id IS NULL AND current_setting('app.current_tenant_id', true) IS NULL)"
        ") WITH CHECK ("
        "tenant_id = current_setting('app.current_tenant_id', true)::uuid "
        "OR (tenant_id IS NULL AND current_setting('app.current_tenant_id', true) IS NULL)"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_events_tenant_isolation ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_mutation ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_block_mutation()")
    op.drop_table("audit_events")
