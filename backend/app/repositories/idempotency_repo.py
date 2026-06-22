"""Idempotency-key repository (tenant-scoped; stores hashes + lock metadata only).

``tenant_id`` may be NULL (webhook/system keys), so lookups match NULL
explicitly rather than via equality (``NULL = NULL`` is never true).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.sql.elements import ColumnElement

from app.models.idempotency_key import IdempotencyKey
from app.repositories.base import BaseRepository


class IdempotencyRepository(BaseRepository):
    @staticmethod
    def _tenant_match(tenant_id: uuid.UUID | None) -> ColumnElement[bool]:
        col = IdempotencyKey.tenant_id
        return col.is_(None) if tenant_id is None else col == tenant_id

    async def get(self, *, tenant_id: uuid.UUID | None, key: str) -> IdempotencyKey | None:
        stmt = select(IdempotencyKey).where(
            self._tenant_match(tenant_id), IdempotencyKey.key == key
        )
        return (await self.conn.execute(stmt)).scalars().first()

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
