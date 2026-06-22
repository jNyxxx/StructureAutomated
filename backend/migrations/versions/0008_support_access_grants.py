"""support_access_grants: time-boxed support access

Revision ID: 0008_support_access_grants
Revises: 0007_auth_sessions
Create Date: 2026-06-22 00:00:07

Support access grants are explicit, time-boxed, revocable, and auditable. They
never grant raw-secret/token/unredacted-PII access by default.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_support_access_grants"
down_revision = "0007_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_access_grants",
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
            "support_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "granted_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index("ix_support_access_grants_tenant_id", "support_access_grants", ["tenant_id"])
    op.create_index(
        "ix_support_access_grants_support_user_id",
        "support_access_grants",
        ["support_user_id"],
    )
    op.create_index(
        "ix_support_access_grants_granted_by_user_id",
        "support_access_grants",
        ["granted_by_user_id"],
    )
    op.create_index(
        "ix_support_access_active_lookup",
        "support_access_grants",
        ["tenant_id", "support_user_id", "scope", "expires_at"],
    )

    op.execute("ALTER TABLE support_access_grants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE support_access_grants FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY support_access_grants_tenant_isolation ON support_access_grants "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS support_access_grants_tenant_isolation ON support_access_grants"
    )
    op.drop_index("ix_support_access_active_lookup", table_name="support_access_grants")
    op.drop_index("ix_support_access_grants_granted_by_user_id", table_name="support_access_grants")
    op.drop_index("ix_support_access_grants_support_user_id", table_name="support_access_grants")
    op.drop_index("ix_support_access_grants_tenant_id", table_name="support_access_grants")
    op.drop_table("support_access_grants")
