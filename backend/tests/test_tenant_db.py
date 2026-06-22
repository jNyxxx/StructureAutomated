"""Tenant DB helper, forced-RLS convention, role-safety, and raw-DB-ban tests (Slice 6).

DB-less: these assert the SQL conventions and source discipline. Live RLS
isolation is exercised once tenant tables exist (Slice 7) against Postgres.
"""

from pathlib import Path

from app.database import (
    ROLE_SAFETY_SQL,
    _tenant_context_statements,
)
from app.db.rls import forced_rls_statements

_BACKEND = Path(__file__).resolve().parents[1]


def test_forced_rls_statements_enable_force_and_policy() -> None:
    stmts = forced_rls_statements("contacts")
    assert "ENABLE ROW LEVEL SECURITY" in stmts[0]
    assert "FORCE ROW LEVEL SECURITY" in stmts[1]
    assert "contacts_tenant_isolation" in stmts[2]
    assert "current_setting('app.current_tenant_id', true)::uuid" in stmts[2]
    assert "USING (" in stmts[2] and "WITH CHECK (" in stmts[2]


def test_tenant_context_is_transaction_local_and_tenant_first() -> None:
    stmts = _tenant_context_statements("11111111-1111-1111-1111-111111111111", "actor-1", "req_1")
    # First statement sets the tenant id; all use is_local=true (SET LOCAL semantics).
    assert "app.current_tenant_id" in stmts[0][0]
    assert all(", true)" in sql for sql, _ in stmts)
    assert stmts[0][1]["v"] == "11111111-1111-1111-1111-111111111111"


def test_tenant_context_omits_optional_when_absent() -> None:
    assert len(_tenant_context_statements("t", None, None)) == 1


def test_role_safety_sql_checks_superuser_and_bypassrls() -> None:
    assert "rolsuper" in ROLE_SAFETY_SQL
    assert "rolbypassrls" in ROLE_SAFETY_SQL


def test_no_raw_db_access_outside_approved_modules() -> None:
    """Only app/database.py may construct engines/connections (CLAUDE.md rule 5)."""
    approved = {Path("app/database.py")}
    forbidden = ("create_async_engine", "create_engine", "asyncpg.connect", "psycopg")
    offenders: list[str] = []
    for path in (_BACKEND / "app").rglob("*.py"):
        rel = path.relative_to(_BACKEND)
        if rel in approved:
            continue
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in forbidden):
            offenders.append(str(rel))
    assert offenders == [], f"raw DB access outside approved modules: {offenders}"
