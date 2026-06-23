"""Offline Alembic SQL render must work without a live DATABASE_URL (MF-4).

``alembic upgrade head --sql`` is the offline DDL-render gate used in CI/evidence.
It must render the full migration chain to SQL **without connecting to — or even
requiring — a database**. Online migrations stay strict (a real DSN is required).

These tests also assert the audit_events forced-RLS DDL (MF-1) appears in the
rendered output, proving the remediation end-to-end against the migration chain.
"""

import contextlib
import io
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.config import get_settings

_ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


def test_offline_sql_render_works_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()
    # Full chain renders to DDL with no DB connection: base table through head.
    assert "CREATE TABLE audit_events" in sql
    assert "CREATE TABLE campaigns" in sql  # head (00012_campaigns) reached


def test_offline_sql_render_includes_audit_events_forced_rls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()
    assert "ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE audit_events FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY audit_events_tenant_isolation ON audit_events" in sql
