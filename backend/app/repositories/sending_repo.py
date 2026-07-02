"""Repository for mock sending and gate evaluation results."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, insert, or_, select, text, update
from sqlalchemy.engine import RowMapping

from app.models.sending import OutboundMessage, SendGateResult
from app.repositories.base import BaseRepository

_GATE_RESULT_COLUMNS = (
    SendGateResult.id,
    SendGateResult.tenant_id,
    SendGateResult.draft_id,
    SendGateResult.status,
    SendGateResult.deny_reason_code,
    SendGateResult.created_at,
)
_OUTBOUND_MESSAGE_COLUMNS = (
    OutboundMessage.id,
    OutboundMessage.tenant_id,
    OutboundMessage.draft_id,
    OutboundMessage.status,
    OutboundMessage.sent_at,
    OutboundMessage.created_at,
    OutboundMessage.updated_at,
)


@dataclass(frozen=True)
class SendGateResultRecord:
    """Read-only representation of a SendGateResult."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    draft_id: uuid.UUID
    status: str
    deny_reason_code: str | None
    created_at: datetime


@dataclass(frozen=True)
class OutboundMessageRecord:
    """Read-only representation of an OutboundMessage."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    draft_id: uuid.UUID
    status: str
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _gate_result(row: RowMapping) -> SendGateResultRecord:
    return SendGateResultRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        draft_id=row["draft_id"],
        status=row["status"],
        deny_reason_code=row["deny_reason_code"],
        created_at=row["created_at"],
    )


def _outbound_message(row: RowMapping) -> OutboundMessageRecord:
    return OutboundMessageRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        draft_id=row["draft_id"],
        status=row["status"],
        sent_at=row["sent_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SendingRepository(BaseRepository):
    """Tenant-scoped repository for mock sending and gate results."""

    async def create_gate_result(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        deny_reason_code: str | None = None,
    ) -> SendGateResultRecord:
        row = (
            (
                await self.conn.execute(
                    insert(SendGateResult)
                    .values(
                        tenant_id=tenant_id,
                        draft_id=draft_id,
                        status=status,
                        deny_reason_code=deny_reason_code,
                    )
                    .returning(*_GATE_RESULT_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _gate_result(row)

    async def get_gate_result_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> SendGateResultRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_GATE_RESULT_COLUMNS).where(
                        SendGateResult.tenant_id == tenant_id,
                        SendGateResult.draft_id == draft_id,
                    )
                )
            )
            .mappings()
            .first()
        )
        return _gate_result(row) if row is not None else None

    async def create_outbound_message(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        sent_at: datetime | None = None,
    ) -> OutboundMessageRecord:
        row = (
            (
                await self.conn.execute(
                    insert(OutboundMessage)
                    .values(
                        tenant_id=tenant_id,
                        draft_id=draft_id,
                        status=status,
                        sent_at=sent_at,
                    )
                    .returning(*_OUTBOUND_MESSAGE_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _outbound_message(row)

    async def get_outbound_message_by_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> OutboundMessageRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_OUTBOUND_MESSAGE_COLUMNS).where(
                        OutboundMessage.tenant_id == tenant_id,
                        OutboundMessage.draft_id == draft_id,
                    )
                )
            )
            .mappings()
            .first()
        )
        return _outbound_message(row) if row is not None else None

    async def list_outbound_messages(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[OutboundMessageRecord], str | None]:
        stmt = select(*_OUTBOUND_MESSAGE_COLUMNS).where(OutboundMessage.tenant_id == tenant_id)
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                return [], None
            cursor_row = (
                (
                    await self.conn.execute(
                        select(*_OUTBOUND_MESSAGE_COLUMNS).where(
                            OutboundMessage.tenant_id == tenant_id,
                            OutboundMessage.id == cursor_id,
                        )
                    )
                )
                .mappings()
                .first()
            )
            if cursor_row is None:
                return [], None
            stmt = stmt.where(
                or_(
                    OutboundMessage.created_at < cursor_row["created_at"],
                    and_(
                        OutboundMessage.created_at == cursor_row["created_at"],
                        OutboundMessage.id < cursor_row["id"],
                    ),
                )
            )

        rows = (
            (
                await self.conn.execute(
                    stmt.order_by(
                        OutboundMessage.created_at.desc(),
                        OutboundMessage.id.desc(),
                    ).limit(limit + 1)
                )
            )
            .mappings()
            .all()
        )
        page_rows = rows[:limit]
        next_cursor = str(page_rows[-1]["id"]) if len(rows) > limit and page_rows else None
        return [_outbound_message(row) for row in page_rows], next_cursor

    async def get_outbound_message_by_id(
        self, *, tenant_id: uuid.UUID, message_id: uuid.UUID
    ) -> OutboundMessageRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_OUTBOUND_MESSAGE_COLUMNS).where(
                        OutboundMessage.tenant_id == tenant_id,
                        OutboundMessage.id == message_id,
                    )
                )
            )
            .mappings()
            .first()
        )
        return _outbound_message(row) if row is not None else None

    async def update_outbound_message_status(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        sent_at: datetime | None = None,
    ) -> OutboundMessageRecord | None:
        values: dict[str, Any] = {"status": status}
        if sent_at is not None:
            values["sent_at"] = sent_at

        values["updated_at"] = text("now()")

        row = (
            (
                await self.conn.execute(
                    update(OutboundMessage)
                    .where(
                        OutboundMessage.tenant_id == tenant_id,
                        OutboundMessage.draft_id == draft_id,
                    )
                    .values(**values)
                    .returning(*_OUTBOUND_MESSAGE_COLUMNS)
                )
            )
            .mappings()
            .first()
        )
        return _outbound_message(row) if row is not None else None
