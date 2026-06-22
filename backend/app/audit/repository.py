"""Audit repository — INSERT/SELECT only (never UPDATE/DELETE)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import insert, select

from app.models.audit_event import AuditEvent
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    async def insert(self, payload: dict[str, Any]) -> None:
        await self.conn.execute(insert(AuditEvent).values(**payload))

    async def list_recent(self) -> list[Any]:
        return list((await self.conn.execute(select(AuditEvent))).all())
