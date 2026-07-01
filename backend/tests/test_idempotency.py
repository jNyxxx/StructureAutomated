"""Idempotency store/service tests (Slice 11).

Deterministic: an in-memory fake repo (no DB) drives the replay/lock semantics,
plus migration-source assertions for DDL. The injected ``now`` keeps every test
clock-free and reproducible.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.repositories.idempotency_repo import IdempotencyRepository
from app.services.idempotency import (
    IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD,
    IdempotencyConflictError,
    IdempotencyService,
    IdempotencyState,
    hash_payload,
)

_NOW = datetime(2026, 6, 22, 12, 0, 0, tzinfo=UTC)
_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0005_idempotency_keys.py"
)


class _Row:
    """Mirror of the columns the service reads back from a persisted row."""

    def __init__(self, *, request_hash: str, locked_until: datetime | None) -> None:
        self.request_hash = request_hash
        self.response_hash: str | None = None
        self.status_code: int | None = None
        self.locked_until = locked_until


class _MappingOnlyResult:
    """Fake SQL result that fails if repository code maps only the scalar id."""

    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row
        self.mappings_called = False

    def mappings(self) -> "_MappingOnlyResult":
        self.mappings_called = True
        return self

    def first(self) -> dict[str, Any]:
        return self.row

    def scalars(self) -> None:
        raise AssertionError("IdempotencyRepository must map full rows, not scalar UUIDs")


class _FakeRepositoryConnection:
    def __init__(self, row: dict[str, Any]) -> None:
        self.result = _MappingOnlyResult(row)
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> _MappingOnlyResult:
        self.statements.append(statement)
        return self.result


class _FakeRepo:
    """In-memory stand-in for IdempotencyRepository keyed on (tenant_id, key)."""

    def __init__(self) -> None:
        self.rows: dict[tuple[Any, str], _Row] = {}

    async def get(self, *, tenant_id: Any, key: str) -> _Row | None:
        return self.rows.get((tenant_id, key))

    async def insert(self, payload: dict[str, Any]) -> None:
        self.rows[(payload["tenant_id"], payload["key"])] = _Row(
            request_hash=payload["request_hash"], locked_until=payload["locked_until"]
        )

    async def relock(self, *, tenant_id: Any, key: str, locked_until: datetime) -> None:
        self.rows[(tenant_id, key)].locked_until = locked_until

    async def mark_completed(
        self, *, tenant_id: Any, key: str, response_hash: str, status_code: int
    ) -> None:
        row = self.rows[(tenant_id, key)]
        row.response_hash = response_hash
        row.status_code = status_code


async def test_idempotency_repository_get_returns_complete_record_without_scalar_mapper() -> None:
    import uuid

    row = {
        "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        "tenant_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "actor_user_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "key": "docker-e2e-key",
        "request_hash": "request-hash",
        "response_hash": "response-hash",
        "status_code": 201,
        "locked_until": None,
        "expires_at": _NOW + timedelta(hours=24),
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = IdempotencyRepository(conn)  # type: ignore[arg-type]

    record = await repo.get(tenant_id=row["tenant_id"], key=row["key"])

    assert record is not None
    assert record.id == row["id"]
    assert record.request_hash == "request-hash"
    assert record.response_hash == "response-hash"
    assert record.status_code == 201
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


def test_hash_payload_is_order_insensitive_for_dicts_and_stable_for_strings() -> None:
    # Worker source: deterministic job dict — key order must not matter.
    assert hash_payload({"a": 1, "b": 2}) == hash_payload({"b": 2, "a": 1})
    # Webhook source: provider event id (string) hashes stably.
    assert hash_payload("evt_123") == hash_payload("evt_123")
    # Different payloads hash differently.
    assert hash_payload({"a": 1}) != hash_payload({"a": 2})


async def test_first_call_proceeds_then_second_replays_stored_response() -> None:
    svc = IdempotencyService(_FakeRepo())  # type: ignore[arg-type]
    body = {"a": 1, "b": 2}

    first = await svc.begin(key="k1", request_payload=body, now=_NOW)
    assert first.state is IdempotencyState.NEW
    assert not first.is_replay

    await svc.complete(key="k1", response_payload={"ok": True}, status_code=201)

    # Same key + same body after completion → replay the stored result, no re-run.
    second = await svc.begin(key="k1", request_payload=body, now=_NOW + timedelta(seconds=1))
    assert second.is_replay
    assert second.state is IdempotencyState.REPLAY
    assert second.status_code == 201
    assert second.response_hash == hash_payload({"ok": True})


async def test_same_key_different_payload_raises_reuse_error() -> None:
    svc = IdempotencyService(_FakeRepo())  # type: ignore[arg-type]
    await svc.begin(key="kk", request_payload={"x": "alpha"}, now=_NOW)

    with pytest.raises(IdempotencyConflictError) as excinfo:
        await svc.begin(key="kk", request_payload={"x": "beta"}, now=_NOW)

    assert excinfo.value.code == IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD
    assert IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD == (
        "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"
    )
    # The error must not leak request-payload contents (CLAUDE.md rule 14).
    assert "alpha" not in str(excinfo.value)
    assert "beta" not in str(excinfo.value)


async def test_lock_blocks_concurrent_double_processing() -> None:
    svc = IdempotencyService(_FakeRepo(), lock_ttl=timedelta(minutes=5))  # type: ignore[arg-type]
    body = {"job": "import"}

    first = await svc.begin(key="job-1", request_payload=body, now=_NOW)
    assert first.state is IdempotencyState.NEW

    # Concurrent retry before completion, still inside the lock window → blocked.
    concurrent = await svc.begin(
        key="job-1", request_payload=body, now=_NOW + timedelta(seconds=30)
    )
    assert concurrent.state is IdempotencyState.IN_PROGRESS
    assert not concurrent.is_replay


async def test_expired_lock_without_completion_allows_fresh_attempt() -> None:
    svc = IdempotencyService(_FakeRepo(), lock_ttl=timedelta(minutes=5))  # type: ignore[arg-type]
    body = {"job": "import"}

    await svc.begin(key="job-2", request_payload=body, now=_NOW)
    # After the lock window with no completion, a retry may proceed again.
    retry = await svc.begin(key="job-2", request_payload=body, now=_NOW + timedelta(minutes=6))
    assert retry.state is IdempotencyState.NEW


def test_model_columns_and_nullable_tenant() -> None:
    from app.models.idempotency_key import IdempotencyKey

    cols = {c.name for c in IdempotencyKey.__table__.columns}
    assert {
        "id",
        "tenant_id",
        "actor_user_id",
        "key",
        "request_hash",
        "response_hash",
        "status_code",
        "locked_until",
        "expires_at",
        "created_at",
    } <= cols
    # tenant_id is nullable so webhook/system keys (no tenant) can be deduped.
    assert IdempotencyKey.__table__.c.tenant_id.nullable is True
    assert IdempotencyKey.__table__.c.key.nullable is False
    assert IdempotencyKey.__table__.c.request_hash.nullable is False
    assert IdempotencyKey.__table__.c.expires_at.nullable is False


def test_migration_forces_rls_with_explicit_system_tenant_handling() -> None:
    src = _MIGRATION.read_text(encoding="utf-8")
    assert "idempotency_keys" in src
    assert 'down_revision = "0004_integration_credentials"' in src
    assert "ix_idempotency_keys_expiry" in src
    # Forced RLS is present on this table.
    assert "ENABLE ROW LEVEL SECURITY" in src
    assert "FORCE ROW LEVEL SECURITY" in src
    assert "CREATE POLICY idempotency_keys_tenant_isolation" in src
    # Tenant rows are isolated by the current tenant context.
    assert "tenant_id = current_setting('app.current_tenant_id', true)::uuid" in src
    # System/NULL-tenant rows are reachable ONLY when no tenant context is set —
    # explicit, not accidentally visible to a tenant request.
    assert "tenant_id IS NULL AND current_setting('app.current_tenant_id', true) IS NULL" in src


def test_migration_blocks_duplicate_null_tenant_keys() -> None:
    src = _MIGRATION.read_text(encoding="utf-8")
    # Tenant rows: partial unique on (tenant_id, key) where tenant_id IS NOT NULL.
    assert "uq_idempotency_keys_tenant_key" in src
    assert 'sa.text("tenant_id IS NOT NULL")' in src
    # System rows: partial unique on (key) ALONE where tenant_id IS NULL, so a
    # second NULL-tenant row with the same key is rejected (a plain UNIQUE would
    # treat the NULL tenant_ids as distinct and allow the duplicate).
    assert "uq_idempotency_keys_system_key" in src
    assert 'sa.text("tenant_id IS NULL")' in src
    # The unsafe plain UNIQUE constraint must be gone.
    assert "UniqueConstraint" not in src
