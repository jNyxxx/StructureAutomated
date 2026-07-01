"""Idempotency-key repository (tenant-scoped; stores hashes + lock metadata only).

``tenant_id`` may be NULL (webhook/system keys), so lookups match NULL
explicitly rather than via equality (``NULL = NULL`` is never true).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import ColumnElement

from app.models.idempotency_key import IdempotencyKey
from app.repositories.base import BaseRepository

_IDEMPOTENCY_COLUMNS = (
    IdempotencyKey.id,
    IdempotencyKey.tenant_id,
    IdempotencyKey.actor_user_id,
    IdempotencyKey.key,
    IdempotencyKey.request_hash,
    IdempotencyKey.response_hash,
    IdempotencyKey.status_code,
    IdempotencyKey.locked_until,
    IdempotencyKey.expires_at,
    IdempotencyKey.created_at,
)


@dataclass(frozen=True)
class IdempotencyRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    key: str
    request_hash: str
    response_hash: str | None
    status_code: int | None
    locked_until: datetime | None
    expires_at: datetime
    created_at: datetime


def _record(row: RowMapping) -> IdempotencyRecord:
    return IdempotencyRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        actor_user_id=row["actor_user_id"],
        key=row["key"],
        request_hash=row["request_hash"],
        response_hash=row["response_hash"],
        status_code=row["status_code"],
        locked_until=row["locked_until"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
    )


class IdempotencyRepository(BaseRepository):
    @staticmethod
    def _tenant_match(tenant_id: uuid.UUID | None) -> ColumnElement[bool]:
        col = IdempotencyKey.tenant_id
        return col.is_(None) if tenant_id is None else col == tenant_id

    async def get(self, *, tenant_id: uuid.UUID | None, key: str) -> IdempotencyRecord | None:
        stmt = select(*_IDEMPOTENCY_COLUMNS).where(
            self._tenant_match(tenant_id), IdempotencyKey.key == key
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        return _record(row) if row is not None else None

    async def insert(self, payload: dict[str, Any]) -> None:
        await self.conn.execute(insert(IdempotencyKey).values(**payload))

    async def relock(
        self, *, tenant_id: uuid.UUID | None, key: str, locked_until: datetime
    ) -> None:
        await self.conn.execute(
            update(IdempotencyKey)
            .where(self._tenant_match(tenant_id), IdempotencyKey.key == key)
            .values(locked_until=locked_until)
        )

    async def mark_completed(
        self, *, tenant_id: uuid.UUID | None, key: str, response_hash: str, status_code: int
    ) -> None:
        await self.conn.execute(
            update(IdempotencyKey)
            .where(self._tenant_match(tenant_id), IdempotencyKey.key == key)
            .values(response_hash=response_hash, status_code=status_code, locked_until=None)
        )
