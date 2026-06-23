"""Queue/outbox service: enqueue, claim, and the run lifecycle.

Postgres is the source of truth for jobs (SQS/EventBridge remain adapter-shaped
and deferred). Enqueue derives a **deterministic idempotency key** from the job
type + payload via the Slice 11 idempotency foundation (``hash_payload``) and
dedupes per tenant. The run lifecycle applies exponential backoff retries and an
explicit dead-letter state once ``max_attempts`` is exhausted. ``last_error``
stores the exception **type only** — never raw error text or secrets (rule 14).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncConnection

from app.database import tenant_session, worker_session
from app.models.job import JobStatus
from app.services.idempotency import hash_payload

DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_LEASE = timedelta(minutes=5)
_BASE_BACKOFF_SECONDS = 10.0
_MAX_BACKOFF_SECONDS = 3600.0
# Safe, non-secret label stored when a job cannot run for lack of tenant context.
_NO_TENANT_CONTEXT = "MissingTenantContext"


@dataclass(frozen=True)
class JobRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    job_type: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    max_attempts: int
    run_after: datetime
    locked_until: datetime | None
    idempotency_key: str
    last_error: str | None


@dataclass(frozen=True)
class ProcessOutcome:
    kind: str  # idle | succeeded | retry | dead_letter | throttled
    claimed: bool


Handler = Callable[[JobRecord, AsyncConnection], Awaitable[None]]

# Context factories let the service open the sanctioned DB context around each
# phase: the cross-tenant claim runs under the worker context; each job's handler
# runs under its own tenant context. Defaults are the real session helpers; tests
# inject fakes. The yielded connection is opaque to the service (it only forwards
# it to the handler), so it is typed Any here.
ClaimContextFactory = Callable[[], AbstractAsyncContextManager[Any]]
TenantContextFactory = Callable[[uuid.UUID], AbstractAsyncContextManager[Any]]


def _default_tenant_context(tenant_id: uuid.UUID) -> AbstractAsyncContextManager[Any]:
    """Per-job tenant context — the same helper HTTP requests use."""
    return tenant_session(tenant_id=tenant_id)


class QueueRepository(Protocol):
    async def get_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, idempotency_key: str
    ) -> JobRecord | None: ...

    async def insert(self, job: JobRecord) -> None: ...

    async def claim_next(self, *, now: datetime, lease: timedelta) -> JobRecord | None: ...

    async def update(self, *, job_id: uuid.UUID, fields: dict[str, Any]) -> None: ...


class ThrottleResult(Protocol):
    # Read-only so impls may expose these as fields or properties (RateLimitResult uses both).
    @property
    def allowed(self) -> bool: ...

    @property
    def retry_after(self) -> int: ...


class ThrottleLike(Protocol):
    async def allow(
        self, *, tenant_id: uuid.UUID | str, job_type: str, now: datetime
    ) -> ThrottleResult: ...


def _safe_error(exc: BaseException) -> str:
    # Exception messages can carry secrets/PII — store only the type name (rule 14).
    return type(exc).__name__


class QueueService:
    def __init__(
        self,
        repo: QueueRepository,
        *,
        lease: timedelta = _DEFAULT_LEASE,
        claim_context: ClaimContextFactory = worker_session,
        tenant_context: TenantContextFactory = _default_tenant_context,
    ) -> None:
        self._repo = repo
        self._lease = lease
        # Sanctioned cross-tenant claim context; per-job tenant context.
        self._claim_context = claim_context
        self._tenant_context = tenant_context

    @staticmethod
    def backoff_delay(attempts: int) -> timedelta:
        """Exponential backoff: base * 2^(attempts-1), capped at the ceiling."""
        seconds = _BASE_BACKOFF_SECONDS * (2 ** max(0, attempts - 1))
        return timedelta(seconds=min(seconds, _MAX_BACKOFF_SECONDS))

    async def enqueue(
        self,
        *,
        tenant_id: uuid.UUID,
        job_type: str,
        payload: dict[str, Any],
        now: datetime,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        idempotency_key: str | None = None,
    ) -> JobRecord:
        key = idempotency_key or hash_payload({"job_type": job_type, "payload": payload})
        existing = await self._repo.get_by_idempotency_key(tenant_id=tenant_id, idempotency_key=key)
        if existing is not None:
            return existing  # deterministic key → dedupe, never duplicate
        job = JobRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            job_type=job_type,
            payload=payload,
            status=JobStatus.QUEUED,
            attempts=0,
            max_attempts=max_attempts,
            run_after=now,
            locked_until=None,
            idempotency_key=key,
            last_error=None,
        )
        await self._repo.insert(job)
        return job

    async def process_next(
        self,
        *,
        now: datetime,
        handler: Handler,
        throttle: ThrottleLike | None = None,
    ) -> ProcessOutcome:
        """Claim one due job, then run it under the job's tenant context.

        The claim is cross-tenant and runs under the sanctioned worker context;
        per-job processing runs under ``tenant_session(job.tenant_id)`` — the same
        helper HTTP requests use — so normal tenant isolation applies while the
        handler runs. A job that carries no tenant context is dead-lettered
        **without running the handler** (fail closed): it can never run safely and
        retrying will not fix it.
        """
        async with self._claim_context():
            job = await self._repo.claim_next(now=now, lease=self._lease)
            if job is None:
                return ProcessOutcome("idle", claimed=False)

            tenant_id: uuid.UUID | None = job.tenant_id
            if tenant_id is None:
                await self._repo.update(
                    job_id=job.id,
                    fields={
                        "status": JobStatus.DEAD_LETTER,
                        "last_error": _NO_TENANT_CONTEXT,
                        "locked_until": None,
                    },
                )
                return ProcessOutcome("no_tenant_context", claimed=True)

            if throttle is not None:
                result = await throttle.allow(
                    tenant_id=job.tenant_id, job_type=job.job_type, now=now
                )
                if not result.allowed:
                    # Release without burning an attempt — back-pressure, not failure.
                    await self._repo.update(
                        job_id=job.id,
                        fields={
                            "status": JobStatus.QUEUED,
                            "run_after": now + timedelta(seconds=max(1, result.retry_after)),
                            "locked_until": None,
                        },
                    )
                    return ProcessOutcome("throttled", claimed=True)

            attempts = job.attempts + 1
            await self._repo.update(
                job_id=job.id,
                fields={"status": JobStatus.RUNNING, "attempts": attempts},
            )

        try:
            # Per-job tenant context: the handler runs under tenant isolation and
            # receives the tenant-scoped connection (symmetric with HTTP requests).
            async with self._tenant_context(tenant_id) as conn:
                await handler(job, conn)
        except Exception as exc:
            # The loop must never crash; capture a safe error and retry or dead-letter.
            fields: dict[str, Any] = {"last_error": _safe_error(exc), "locked_until": None}
            if attempts >= job.max_attempts:
                fields["status"] = JobStatus.DEAD_LETTER
                await self._mark(job.id, fields)
                return ProcessOutcome("dead_letter", claimed=True)
            fields["status"] = JobStatus.FAILED
            fields["run_after"] = now + self.backoff_delay(attempts)
            await self._mark(job.id, fields)
            return ProcessOutcome("retry", claimed=True)

        await self._mark(job.id, {"status": JobStatus.SUCCEEDED, "locked_until": None})
        return ProcessOutcome("succeeded", claimed=True)

    async def _mark(self, job_id: uuid.UUID, fields: dict[str, Any]) -> None:
        """Persist a job-row status change under the worker (claim) context."""
        async with self._claim_context():
            await self._repo.update(job_id=job_id, fields=fields)
