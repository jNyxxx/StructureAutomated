"""Alembic migration: add platform_admin to tenant_memberships role constraint.

Adds `platform_admin` to the `ck_tenant_memberships_role` CHECK constraint.
Permissions are limited to platform routes only — no tenant data access,
no RLS bypass, no tenant-owner powers. MFA enforcement activates automatically
via the already-wired enforce_mfa() in auth/dependencies.py.

`support` is intentionally kept out of tenant_memberships.role: support access
is grant-based (SupportAccessService, time-boxed, audited) not membership-based.

Revision ID: 00022_platform_admin_role
Revises: 00021_outcomes
Create Date: 2026-06-28 00:00:22
"""

from __future__ import annotations

from alembic import op

revision = "00022_platform_admin_role"
down_revision = "00021_outcomes"
branch_labels = None
depends_on = None

_ROLES_NEW = (
    "owner",
    "admin",
    "marketer",
    "reviewer",
    "viewer",
    "billing_admin",
    "platform_admin",
)
_ROLES_OLD = (
    "owner",
    "admin",
    "marketer",
    "reviewer",
    "viewer",
    "billing_admin",
)
_CONSTRAINT = "ck_tenant_memberships_role"
_TABLE = "tenant_memberships"


def _role_check(roles: tuple[str, ...]) -> str:
    role_list = ", ".join(f"'{r}'" for r in roles)
    return f"role IN ({role_list})"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, _role_check(_ROLES_NEW))


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_="check")
    op.create_check_constraint(_CONSTRAINT, _TABLE, _role_check(_ROLES_OLD))
