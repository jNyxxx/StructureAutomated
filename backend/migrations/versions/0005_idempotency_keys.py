"""idempotency_keys: retry-safe replay store (request/response hashes + lock)

Revision ID: 0005_idempotency_keys
Revises: 0004_integration_credentials
Create Date: 2026-06-22 00:00:04

tenant_id is nullable (webhook/system keys carry no tenant). Forced RLS isolates
tenant rows to their own tenant context; system/NULL-tenant rows are reachable
ONLY when no tenant context is set (worker/webhook system path) — never by a
tenant request. Uniqueness uses two partial unique indexes so a NULL-tenant key
cannot be duplicated (a plain UNIQUE treats NULLs as distinct). Stores only
hashes of request/response payloads, never the raw payloads.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_idempotency_keys"
down_revision = "0004_integration_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
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
            nullable=True,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("key", sa.Text, nullable=False),
        sa.Column("request_hash", sa.Text, nullable=False),
        sa.Column("response_hash", sa.Text, nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Tenant rows: unique on (tenant_id, key).
    op.create_index(
        "uq_idempotency_keys_tenant_key",
        "idempotency_keys",
        ["tenant_id", "key"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )
    # System rows: unique on (key) alone — blocks duplicate NULL-tenant keys.
    op.create_index(
        "uq_idempotency_keys_system_key",
        "idempotency_keys",
        ["key"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )
    op.create_index("ix_idempotency_keys_expiry", "idempotency_keys", ["expires_at"])

    # Forced RLS with explicit, safe NULL-tenant handling. Tenant rows match the
    # current tenant context; system (NULL-tenant) rows are visible ONLY when no
    # tenant context is set. Identical USING + WITH CHECK so a tenant request can
    # neither read nor write system rows, and vice versa. Predicate is a static
    # literal (no interpolation) — table/columns are developer-controlled.
    op.execute("ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY idempotency_keys_tenant_isolation ON idempotency_keys USING ("
        "tenant_id = current_setting('app.current_tenant_id', true)::uuid "
        "OR (tenant_id IS NULL AND current_setting('app.current_tenant_id', true) IS NULL)"
        ") WITH CHECK ("
        "tenant_id = current_setting('app.current_tenant_id', true)::uuid "
        "OR (tenant_id IS NULL AND current_setting('app.current_tenant_id', true) IS NULL)"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS idempotency_keys_tenant_isolation ON idempotency_keys")
    op.drop_index("ix_idempotency_keys_expiry", table_name="idempotency_keys")
    op.drop_index("uq_idempotency_keys_system_key", table_name="idempotency_keys")
    op.drop_index("uq_idempotency_keys_tenant_key", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
