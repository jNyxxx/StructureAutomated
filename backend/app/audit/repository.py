"""Audit repository — INSERT/SELECT only (never UPDATE/DELETE)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, insert, or_, select
from sqlalchemy.engine import RowMapping

from app.models.audit_event import AuditEvent
from app.repositories.base import BaseRepository
from app.services.settings_api import AuditEventReadRecord

_AUDIT_EVENT_COLUMNS = (
    AuditEvent.id,
    AuditEvent.event_type,
    AuditEvent.actor_user_id,
    AuditEvent.object_type,
    AuditEvent.object_id,
    AuditEvent.request_id,
    AuditEvent.job_id,
    AuditEvent.redacted_details,
    AuditEvent.created_at,
)


def _audit_record(row: RowMapping) -> AuditEventReadRecord:
    return AuditEventReadRecord(
        id=row["id"],
        event_type=row["event_type"],
        actor_user_id=row["actor_user_id"],
        object_type=row["object_type"],
        object_id=row["object_id"],
        request_id=row["request_id"],
        job_id=row["job_id"],
        redacted_details=row["redacted_details"],
        created_at=row["created_at"],
    )


class AuditRepository(BaseRepository):
    async def insert(self, payload: dict[str, Any]) -> None:
        await self.conn.execute(insert(AuditEvent).values(**payload))

    async def list_recent(self) -> list[Any]:
        return list((await self.conn.execute(select(AuditEvent))).all())

    async def list_recent_bounded(
        self, *, cursor: str | None, limit: int
    ) -> tuple[list[AuditEventReadRecord], str | None]:
        stmt = select(*_AUDIT_EVENT_COLUMNS)
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                return [], None
            cursor_row = (
                (
                    await self.conn.execute(
                        select(*_AUDIT_EVENT_COLUMNS).where(AuditEvent.id == cursor_id)
                    )
                )
                .mappings()
                .first()
            )
            if cursor_row is None:
                return [], None
            stmt = stmt.where(
                or_(
                    AuditEvent.created_at < cursor_row["created_at"],
                    and_(
                        AuditEvent.created_at == cursor_row["created_at"],
                        AuditEvent.id < cursor_row["id"],
                    ),
                )
            )
        rows = (
            (
                await self.conn.execute(
                    stmt.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(
                        limit + 1
                    )
                )
            )
            .mappings()
            .all()
        )
        page_rows = rows[:limit]
        next_cursor = str(page_rows[-1]["id"]) if len(rows) > limit and page_rows else None
        return [_audit_record(row) for row in page_rows], next_cursor
