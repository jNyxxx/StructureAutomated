"""Audit service redaction + append-only migration assertions (Slice 8).

DB-less. Live immutability (UPDATE/DELETE rejected) runs against Postgres in CI.
"""

import uuid
from pathlib import Path

from app.audit.service import AuditService

_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0003_audit_events.py"
)


def test_build_payload_redacts_and_omits_created_at() -> None:
    payload = AuditService.build_payload(
        event_type="auth.login",
        tenant_id=uuid.uuid4(),
        details={"ip": "1.2.3.4", "password": "SENTINEL", "nested": {"api_key": "sk_x"}},
    )
    assert payload["event_type"] == "auth.login"
    assert "created_at" not in payload  # server-set
    details = payload["redacted_details"]
    assert details["ip"] == "1.2.3.4"
    assert details["password"] == "***REDACTED***"
    assert details["nested"]["api_key"] == "***REDACTED***"


def test_migration_enforces_append_only_and_shape() -> None:
    src = _MIGRATION.read_text(encoding="utf-8")
    assert "BEFORE UPDATE OR DELETE ON audit_events" in src
    assert "audit_events is append-only" in src
    assert "GRANT INSERT, SELECT ON audit_events TO app_role" in src
    assert "REVOKE UPDATE, DELETE ON audit_events FROM app_role" in src
    assert "ix_audit_events_tenant_created_at" in src
    assert "created_at DESC" in src
    assert "ix_audit_events_object" in src
    assert "redacted_details" in src


def test_migration_enforces_forced_rls_with_null_aware_tenant_policy() -> None:
    """MF-1: audit_events was the only tenant-owned table missing forced RLS.

    The NULL-aware policy mirrors idempotency_keys: a tenant request (tenant
    context set) sees ONLY its own rows; platform/system rows (tenant_id IS NULL)
    are reachable ONLY when no tenant context is set — never by a tenant request.
    """
    src = _MIGRATION.read_text(encoding="utf-8")
    assert "ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY" in src
    assert "ALTER TABLE audit_events FORCE ROW LEVEL SECURITY" in src
    assert "CREATE POLICY audit_events_tenant_isolation ON audit_events" in src
    assert "tenant_id = current_setting('app.current_tenant_id', true)::uuid" in src
    assert "tenant_id IS NULL AND current_setting('app.current_tenant_id', true) IS NULL" in src
    # Platform/system audit rows must NOT be exposed via a worker-context bypass
    # (unlike jobs): audit isolation is strictly tenant / NULL-aware.
    assert "app.worker_context" not in src
