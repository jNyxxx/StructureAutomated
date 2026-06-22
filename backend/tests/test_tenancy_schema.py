"""Core tenancy schema, constraints, and forced-RLS tests (Slice 7).

DB-less metadata + migration-source assertions. Live RLS isolation and
upgrade/downgrade run against Postgres in CI.
"""

from pathlib import Path

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models import ROLES, Tenant, TenantMembership, User

_FORBIDDEN = {"client_id", "workspace_id", "account_id"}
_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0002_core_tenancy.py"
)


def _columns(model: type) -> set[str]:
    return {c.name for c in model.__table__.columns}  # type: ignore[attr-defined]


def _unique_colsets(model: type) -> list[frozenset[str]]:
    return [
        frozenset(c.name for c in con.columns)
        for con in model.__table__.constraints  # type: ignore[attr-defined]
        if isinstance(con, UniqueConstraint)
    ]


def test_users_identity_and_email_unique() -> None:
    sets = _unique_colsets(User)
    assert frozenset({"identity_provider", "provider_user_id"}) in sets
    assert frozenset({"email"}) in sets
    assert "tenant_id" not in _columns(User)  # global identity


def test_membership_unique_and_role_check_and_tenant_not_null() -> None:
    assert frozenset({"tenant_id", "user_id"}) in _unique_colsets(TenantMembership)
    assert TenantMembership.__table__.c.tenant_id.nullable is False
    checks = [
        str(c.sqltext)
        for c in TenantMembership.__table__.constraints  # type: ignore[attr-defined]
        if isinstance(c, CheckConstraint)
    ]
    assert any(all(role in ck for role in ROLES) for ck in checks)


def test_no_forbidden_tenant_columns() -> None:
    for model in (Tenant, User, TenantMembership):
        assert _columns(model).isdisjoint(_FORBIDDEN)


def test_migration_applies_forced_rls_correctly() -> None:
    src = _MIGRATION.read_text(encoding="utf-8")
    # tenants: forced RLS keyed on its own id
    assert "ALTER TABLE tenants FORCE ROW LEVEL SECURITY" in src
    assert "id = current_setting('app.current_tenant_id', true)::uuid" in src
    # tenant_memberships: standard forced-RLS convention
    assert 'apply_forced_rls("tenant_memberships")' in src
    # users stays global identity — never RLS-enabled
    assert "ALTER TABLE users ENABLE ROW LEVEL SECURITY" not in src
