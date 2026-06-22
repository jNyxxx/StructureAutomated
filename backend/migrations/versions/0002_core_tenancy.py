"""core tenancy: tenants, users (clerk identity), tenant_memberships + forced RLS

Revision ID: 0002_core_tenancy
Revises: 0001_extensions
Create Date: 2026-06-22 00:00:01

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import apply_forced_rls

revision = "0002_core_tenancy"
down_revision = "0001_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column(
            "settings", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
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
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('active','suspended','deleted')", name="ck_tenants_status"),
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("email", postgresql.CITEXT, nullable=False),
        sa.Column("identity_provider", sa.String(50), nullable=False, server_default="clerk"),
        sa.Column("provider_user_id", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255)),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("identity_provider", "provider_user_id", name="uq_users_identity"),
    )

    op.create_table(
        "tenant_memberships",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('owner','admin','marketer','reviewer','viewer','billing_admin')",
            name="ck_tenant_memberships_role",
        ),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_user"),
    )
    op.create_index("ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"])

    # Forced RLS. tenants is keyed on its own id; tenant_memberships uses the
    # standard tenant_id convention. users is global identity → no tenant RLS.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenants_self_isolation ON tenants "
        "USING (id = current_setting('app.current_tenant_id', true)::uuid) "
        "WITH CHECK (id = current_setting('app.current_tenant_id', true)::uuid)"
    )
    apply_forced_rls("tenant_memberships")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_memberships_tenant_isolation ON tenant_memberships")
    op.execute("DROP POLICY IF EXISTS tenants_self_isolation ON tenants")
    op.drop_index("ix_tenant_memberships_user_id", table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_table("users")
    op.drop_table("tenants")
