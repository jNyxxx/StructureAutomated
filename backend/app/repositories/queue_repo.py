"""Queue repository: durable job rows + concurrency-safe claim.

``claim_next`` leases exactly one due row using ``FOR UPDATE SKIP LOCKED`` so
concurrent workers never claim the same job. Cross-tenant visibility for the
claim comes from the worker-context RLS clause (set via ``worker_session``);
per-job processing then runs under ``tenant_session`` for normal isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.engine import RowMapping

from app.models.job import Job, JobStatus
from app.repositories.base import BaseRepository
from app.services.queue import JobRecord

_COLUMNS = (
    Job.id,
    Job.tenant_id,
    Job.job_type,
    Job.payload,
    Job.status,
    Job.attempts,
    Job.max_attempts,
    Job.run_after,
    Job.locked_until,
    Job.idempotency_key,
    Job.last_error,
)

# Lock one due row without blocking on rows other workers already hold. Excludes
# terminal states; an expired lease (locked_until past) is reclaimable.
_CLAIM_SQL = text(
    "SELECT id FROM jobs "
    "WHERE status NOT IN ('succeeded', 'dead_letter', 'canceled') AND run_after <= :now "
    "AND (locked_until IS NULL OR locked_until <= :now) "
    "ORDER BY run_after FOR UPDATE SKIP LOCKED LIMIT 1"
)


def _record(row: RowMapping) -> JobRecord:
    return JobRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        job_type=row["job_type"],
        payload=row["payload"],
        status=JobStatus(row["status"]),
        attempts=row["attempts"],
        max_attempts=row["max_attempts"],
        run_after=row["run_after"],
        locked_until=row["locked_until"],
        idempotency_key=row["idempotency_key"],
        last_error=row["last_error"],
    )


class QueueRepository(BaseRepository):
    async def get_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, idempotency_key: str
    ) -> JobRecord | None:
        stmt = select(*_COLUMNS).where(
            Job.tenant_id == tenant_id, Job.idempotency_key == idempotency_key
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        return _record(row) if row is not None else None

    async def insert(self, job: JobRecord) -> None:
        await self.conn.execute(
            insert(Job).values(
                id=job.id,
                tenant_id=job.tenant_id,
                job_type=job.job_type,
                payload=job.payload,
                status=job.status,
                attempts=job.attempts,
                max_attempts=job.max_attempts,
                run_after=job.run_after,
                locked_until=job.locked_until,
                idempotency_key=job.idempotency_key,
                last_error=job.last_error,
            )
        )

    async def claim_next(self, *, now: datetime, lease: timedelta) -> JobRecord | None:
        job_id = (await self.conn.execute(_CLAIM_SQL, {"now": now})).scalar_one_or_none()
        if job_id is None:
            return None
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.LEASED, locked_until=now + lease, updated_at=now)
            .returning(*_COLUMNS)
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        return _record(row) if row is not None else None

    async def update(self, *, job_id: uuid.UUID, fields: dict[str, Any]) -> None:
        # Persistence stamps updated_at; the service passes only domain fields.
        await self.conn.execute(
            update(Job).where(Job.id == job_id).values(**fields, updated_at=func.now())
        )
