"""auth_sessions: app-side Clerk mapping/revocation metadata

Revision ID: 0007_auth_sessions
Revises: 0006_jobs
Create Date: 2026-06-22 00:00:06

Clerk owns credentials, login, primary sessions, password reset, email
verification, MFA support, and primary auth security. The app stores only a
provider session reference for app-side revocation/audit and a membership
version snapshot. No raw tokens, passwords, refresh tokens, or provider secrets
are stored.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_auth_sessions"
down_revision = "0006_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_memberships",
        sa.Column("membership_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "auth_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("provider_session_ref", sa.Text(), nullable=False),
        sa.Column("membership_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_tenant_id", "auth_sessions", ["tenant_id"])
    op.create_index(
        "ix_auth_sessions_provider_session_ref", "auth_sessions", ["provider_session_ref"]
    )

    # Forced RLS. Tenant-scoped reads see their tenant rows; pre-tenant auth
    # plumbing uses app.auth_context='on' to check revocation without setting
    # tenant context before a principal is resolved. Static literal only.
    op.execute("ALTER TABLE auth_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE auth_sessions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY auth_sessions_auth_or_tenant ON auth_sessions USING ("
        "current_setting('app.auth_context', true) = 'on' "
        "OR tenant_id = current_setting('app.current_tenant_id', true)::uuid"
        ") WITH CHECK ("
        "current_setting('app.auth_context', true) = 'on' "
        "OR tenant_id = current_setting('app.current_tenant_id', true)::uuid"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS auth_sessions_auth_or_tenant ON auth_sessions")
    op.drop_index("ix_auth_sessions_provider_session_ref", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_tenant_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_column("tenant_memberships", "membership_version")
