"""Queue/outbox + worker-loop foundation tests (Slice 13).

Deterministic: an in-memory fake repo drives enqueue/claim/retry/DLQ/throttle
semantics with an injected ``now``; the migration DDL (columns, statuses, forced
RLS, indexes) is checked from source. No live DB required (live claim/retry
smoke is deferred to CI).
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.models.job import JobStatus
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.services.idempotency import hash_payload
from app.services.queue import JobRecord, QueueService
from app.services.rate_limit import RateLimitPolicy, RateLimitService
from app.workers.throttle import JobThrottle
from app.workers.worker import WorkerLoop

_NOW = datetime(2026, 6, 22, 12, 0, 0, tzinfo=UTC)
_LEASE = timedelta(minutes=5)
_T_A = uuid.UUID(int=1)
_T_B = uuid.UUID(int=2)
_MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0006_jobs.py"


class _FakeQueueRepo:
    """In-memory job store keyed on job id; claim is global (cross-tenant)."""

    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, JobRecord] = {}

    async def get_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, idempotency_key: str
    ) -> JobRecord | None:
        for row in self.rows.values():
            if row.tenant_id == tenant_id and row.idempotency_key == idempotency_key:
                return row
        return None

    async def get_for_tenant(self, *, tenant_id: uuid.UUID, job_id: uuid.UUID) -> JobRecord | None:
        row = self.rows.get(job_id)
        return row if row is not None and row.tenant_id == tenant_id else None

    async def insert(self, job: JobRecord) -> None:
        self.rows[job.id] = job

    async def claim_next(self, *, now: datetime, lease: timedelta) -> JobRecord | None:
        terminal = (JobStatus.SUCCEEDED, JobStatus.DEAD_LETTER, JobStatus.CANCELED)
        claimable = [
            r
            for r in self.rows.values()
            if r.status not in terminal
            and r.run_after <= now
            and (r.locked_until is None or r.locked_until <= now)
        ]
        if not claimable:
            return None
        row = sorted(claimable, key=lambda r: r.run_after)[0]
        leased = replace(row, status=JobStatus.LEASED, locked_until=now + lease)
        self.rows[row.id] = leased
        return leased

    async def update(self, *, job_id: uuid.UUID, fields: dict[str, Any]) -> None:
        self.rows[job_id] = replace(self.rows[job_id], **fields)

    def only(self) -> JobRecord:
        return next(iter(self.rows.values()))


@asynccontextmanager
async def _noop_ctx(*_args: object) -> AsyncIterator[None]:
    """Do-nothing claim/tenant context for tests that don't inspect scoping."""
    yield None


def _make_service(repo: _FakeQueueRepo) -> QueueService:
    """QueueService wired with no-op contexts so process_next needs no live DB."""
    return QueueService(repo, claim_context=_noop_ctx, tenant_context=_noop_ctx)


class _CtxLog:
    """Records context enter/exit so tests can assert claim vs tenant scoping."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, uuid.UUID | None]] = []


class _RecordingCtx:
    def __init__(self, log: _CtxLog, kind: str, tenant_id: uuid.UUID | None = None) -> None:
        self._log = log
        self._kind = kind
        self._tid = tenant_id

    async def __aenter__(self) -> str:
        self._log.events.append(("enter", self._kind, self._tid))
        return f"conn:{self._kind}:{self._tid}"

    async def __aexit__(self, *exc: object) -> bool:
        self._log.events.append(("exit", self._kind, self._tid))
        return False


def _recording_contexts(log: _CtxLog) -> tuple[Any, Any]:
    def claim() -> _RecordingCtx:
        return _RecordingCtx(log, "worker")

    def tenant(tenant_id: uuid.UUID) -> _RecordingCtx:
        return _RecordingCtx(log, "tenant", tenant_id)

    return claim, tenant


async def _ok_handler(job: JobRecord, conn: object) -> None:
    return None


async def test_enqueue_creates_queued_job_with_deterministic_idempotency_key() -> None:
    svc = QueueService(_FakeQueueRepo())
    job = await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={"x": 1}, now=_NOW)

    assert job.status == JobStatus.QUEUED
    assert job.attempts == 0
    assert job.run_after == _NOW
    assert job.idempotency_key == hash_payload({"job_type": "noop", "payload": {"x": 1}})


async def test_enqueue_dedupes_within_tenant_and_isolates_across_tenants() -> None:
    repo = _FakeQueueRepo()
    svc = QueueService(repo)

    a1 = await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={"x": 1}, now=_NOW)
    a2 = await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={"x": 1}, now=_NOW)
    b1 = await svc.enqueue(tenant_id=_T_B, job_type="noop", payload={"x": 1}, now=_NOW)

    assert a1.id == a2.id  # same key + tenant → deduped, not duplicated
    assert b1.id != a1.id  # same key, different tenant → distinct job
    assert len(repo.rows) == 2


async def test_claim_and_succeed() -> None:
    repo = _FakeQueueRepo()
    svc = _make_service(repo)
    await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={}, now=_NOW)

    seen: list[uuid.UUID] = []

    async def handler(job: JobRecord, conn: object) -> None:
        seen.append(job.id)

    outcome = await svc.process_next(now=_NOW, handler=handler)

    assert outcome.kind == "succeeded"
    job = repo.only()
    assert job.status == JobStatus.SUCCEEDED
    assert job.attempts == 1
    assert job.locked_until is None
    assert len(seen) == 1


async def test_idle_when_nothing_claimable() -> None:
    svc = _make_service(_FakeQueueRepo())
    outcome = await svc.process_next(now=_NOW, handler=_ok_handler)
    assert outcome.kind == "idle"
    assert outcome.claimed is False


async def test_failure_retries_with_backoff_then_dead_letters_with_safe_error() -> None:
    repo = _FakeQueueRepo()
    svc = _make_service(repo)
    await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={}, now=_NOW, max_attempts=2)

    async def boom(job: JobRecord, conn: object) -> None:
        raise RuntimeError("boom SENTINELSECRET token=abc123")

    first = await svc.process_next(now=_NOW, handler=boom)
    assert first.kind == "retry"
    job = repo.only()
    assert job.status == JobStatus.FAILED
    assert job.attempts == 1
    assert job.run_after > _NOW  # backoff scheduled
    assert job.locked_until is None
    # last_error must be safe — no raw exception message / secret leaks through.
    assert job.last_error is not None
    assert "SENTINELSECRET" not in job.last_error
    assert "token=abc123" not in job.last_error

    # Not yet claimable (still in backoff window).
    assert (await svc.process_next(now=_NOW, handler=boom)).kind == "idle"

    # After the backoff elapses, the second attempt exhausts max_attempts → dead-letter.
    second = await svc.process_next(now=job.run_after, handler=boom)
    assert second.kind == "dead_letter"
    dead = repo.only()
    assert dead.status == JobStatus.DEAD_LETTER
    assert dead.attempts == 2


async def test_lease_blocks_concurrent_claim_until_expiry() -> None:
    repo = _FakeQueueRepo()
    svc = QueueService(repo)
    await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={}, now=_NOW)

    first = await repo.claim_next(now=_NOW, lease=_LEASE)
    assert first is not None
    assert first.status == JobStatus.LEASED
    # Second claim within the lease window finds nothing (row is locked).
    assert await repo.claim_next(now=_NOW + timedelta(seconds=30), lease=_LEASE) is None
    # After the lease expires the row is reclaimable.
    reclaimed = await repo.claim_next(now=_NOW + _LEASE + timedelta(seconds=1), lease=_LEASE)
    assert reclaimed is not None


async def test_throttle_defers_job_without_consuming_an_attempt() -> None:
    repo = _FakeQueueRepo()
    svc = _make_service(repo)
    await svc.enqueue(tenant_id=_T_A, job_type="send", payload={}, now=_NOW)

    rl = RateLimitService(InMemoryRateLimitBackend())
    throttle = JobThrottle(rl, RateLimitPolicy("job", limit=1, window=timedelta(minutes=1)))
    # Exhaust the per-(tenant, job_type) allowance.
    await throttle.allow(tenant_id=_T_A, job_type="send", now=_NOW)

    async def must_not_run(job: JobRecord, conn: object) -> None:
        raise AssertionError("handler ran while throttled")

    outcome = await svc.process_next(now=_NOW, handler=must_not_run, throttle=throttle)

    assert outcome.kind == "throttled"
    job = repo.only()
    assert job.status == JobStatus.QUEUED  # released back for later
    assert job.attempts == 0  # throttling does not burn an attempt
    assert job.run_after > _NOW


def test_backoff_is_monotonic_and_capped() -> None:
    d1 = QueueService.backoff_delay(1)
    d2 = QueueService.backoff_delay(2)
    d3 = QueueService.backoff_delay(3)
    assert d1 < d2 < d3
    # Eventually capped: very large attempt counts converge to the same ceiling.
    assert QueueService.backoff_delay(100) == QueueService.backoff_delay(1000)


async def test_worker_loop_runs_once_and_is_stoppable() -> None:
    repo = _FakeQueueRepo()
    svc = _make_service(repo)
    await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={}, now=_NOW)

    processed: list[uuid.UUID] = []

    async def handler(job: JobRecord, conn: object) -> None:
        processed.append(job.id)

    loop = WorkerLoop(svc, handler)
    outcome = await loop.run_once(now=_NOW)
    assert outcome.kind == "succeeded"
    assert len(processed) == 1

    # Stoppable: stop() before run() makes the loop exit immediately (no hang/sleep).
    loop.stop()
    await loop.run(now_fn=lambda: _NOW)


async def test_handler_runs_inside_tenant_context_with_its_connection() -> None:
    repo = _FakeQueueRepo()
    log = _CtxLog()
    claim, tenant = _recording_contexts(log)
    svc = QueueService(repo, claim_context=claim, tenant_context=tenant)
    await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={}, now=_NOW)

    seen: list[tuple[uuid.UUID, object, list[tuple[str, str, uuid.UUID | None]]]] = []

    async def handler(job: JobRecord, conn: object) -> None:
        seen.append((job.tenant_id, conn, list(log.events)))

    outcome = await svc.process_next(now=_NOW, handler=handler)

    assert outcome.kind == "succeeded"
    assert len(seen) == 1
    tid, conn, events_when_called = seen[0]
    assert tid == _T_A
    # Handler received the tenant-scoped connection for its own tenant.
    assert conn == f"conn:tenant:{_T_A}"
    # The tenant context was open (entered, not yet exited) while the handler ran.
    assert ("enter", "tenant", _T_A) in events_when_called
    assert ("exit", "tenant", _T_A) not in events_when_called


async def test_missing_tenant_context_fails_closed_without_running_handler() -> None:
    repo = _FakeQueueRepo()
    log = _CtxLog()
    claim, tenant = _recording_contexts(log)
    svc = QueueService(repo, claim_context=claim, tenant_context=tenant)
    # Defensive: tenant_id is NOT NULL at the DB, but a job that somehow lacks
    # tenant context must never run — fail closed (dead-letter, no handler).
    await repo.insert(
        JobRecord(
            id=uuid.uuid4(),
            tenant_id=None,  # type: ignore[arg-type]
            job_type="noop",
            payload={},
            status=JobStatus.QUEUED,
            attempts=0,
            max_attempts=3,
            run_after=_NOW,
            locked_until=None,
            idempotency_key="k",
            last_error=None,
        )
    )

    ran = False

    async def handler(job: JobRecord, conn: object) -> None:
        nonlocal ran
        ran = True

    outcome = await svc.process_next(now=_NOW, handler=handler)

    assert outcome.kind == "no_tenant_context"
    assert ran is False
    # No tenant context was ever entered (fail closed before the handler).
    assert all(kind != "tenant" for _, kind, _ in log.events)
    dead = repo.only()
    assert dead.status == JobStatus.DEAD_LETTER
    assert dead.last_error is not None
    assert "token" not in dead.last_error  # safe, non-secret label only


async def test_claim_uses_worker_context_and_handler_never_runs_under_it() -> None:
    repo = _FakeQueueRepo()
    log = _CtxLog()
    claim, tenant = _recording_contexts(log)
    svc = QueueService(repo, claim_context=claim, tenant_context=tenant)
    await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={}, now=_NOW)

    events_during_handler: list[list[tuple[str, str, uuid.UUID | None]]] = []

    async def handler(job: JobRecord, conn: object) -> None:
        events_during_handler.append(list(log.events))

    await svc.process_next(now=_NOW, handler=handler)

    # The claim ran under the sanctioned worker context.
    assert ("enter", "worker", None) in log.events
    # No worker context was held open while the handler ran (only tenant context).
    snapshot = events_during_handler[0]
    opened = snapshot.count(("enter", "worker", None))
    closed = snapshot.count(("exit", "worker", None))
    assert opened - closed == 0
    assert ("enter", "tenant", _T_A) in snapshot


async def test_each_job_runs_under_its_own_tenant_context_no_cross_tenant() -> None:
    repo = _FakeQueueRepo()
    log = _CtxLog()
    claim, tenant = _recording_contexts(log)
    svc = QueueService(repo, claim_context=claim, tenant_context=tenant)
    await svc.enqueue(tenant_id=_T_A, job_type="noop", payload={}, now=_NOW)
    await svc.enqueue(tenant_id=_T_B, job_type="noop", payload={}, now=_NOW)

    ran_under: list[tuple[uuid.UUID, object]] = []

    async def handler(job: JobRecord, conn: object) -> None:
        ran_under.append((job.tenant_id, conn))

    await svc.process_next(now=_NOW, handler=handler)
    await svc.process_next(now=_NOW, handler=handler)

    # Each handler ran under exactly its own tenant's context/connection.
    assert len(ran_under) == 2
    for tid, conn in ran_under:
        assert conn == f"conn:tenant:{tid}"
    tenant_ctx_used = {t for ev, kind, t in log.events if ev == "enter" and kind == "tenant"}
    assert tenant_ctx_used == {_T_A, _T_B}


def test_model_has_required_columns_and_tenant_not_null() -> None:
    from app.models.job import Job

    cols = {c.name for c in Job.__table__.columns}
    assert {
        "id",
        "tenant_id",
        "job_type",
        "payload",
        "status",
        "attempts",
        "max_attempts",
        "run_after",
        "locked_until",
        "idempotency_key",
        "last_error",
        "created_at",
        "updated_at",
    } <= cols
    assert Job.__table__.c.tenant_id.nullable is False
    assert Job.__table__.c.idempotency_key.nullable is False


def test_migration_creates_jobs_with_forced_rls_indexes_and_status_check() -> None:
    src = _MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "0005_idempotency_keys"' in src
    assert '"jobs"' in src
    # Columns the contract requires.
    for col in ("job_type", "payload", "attempts", "max_attempts", "run_after", "idempotency_key"):
        assert col in src
    # Forced RLS with the worker-context claim clause.
    assert "ENABLE ROW LEVEL SECURITY" in src
    assert "FORCE ROW LEVEL SECURITY" in src
    assert "CREATE POLICY jobs_tenant_isolation" in src
    assert "tenant_id = current_setting('app.current_tenant_id', true)::uuid" in src
    assert "current_setting('app.worker_context', true) = 'on'" in src
    # Canonical statuses present in the CHECK constraint.
    for status in ("queued", "running", "succeeded", "failed", "dead_letter"):
        assert status in src
    # Dedup + worker claim indexes.
    assert "uq_jobs_tenant_idempotency_key" in src
    assert "ix_jobs_status_run_after" in src
