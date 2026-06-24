"""Repository for follow-up rules and schedules."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, insert, or_, select, update

from app.models.followup import FollowUpRule, FollowUpSchedule
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class FollowUpRuleRecord:
    """Read-only representation of a FollowUpRule."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    delay_seconds: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FollowUpScheduleRecord:
    """Read-only representation of a FollowUpSchedule."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    original_outbound_message_id: uuid.UUID
    original_draft_id: uuid.UUID
    followup_rule_id: uuid.UUID
    status: str
    run_after: datetime
    actor_user_id: uuid.UUID
    actor_role: str
    created_at: datetime
    updated_at: datetime


def _rule(row: FollowUpRule) -> FollowUpRuleRecord:
    return FollowUpRuleRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        campaign_id=row.campaign_id,
        delay_seconds=row.delay_seconds,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _schedule(row: FollowUpSchedule) -> FollowUpScheduleRecord:
    return FollowUpScheduleRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        campaign_id=row.campaign_id,
        contact_id=row.contact_id,
        original_outbound_message_id=row.original_outbound_message_id,
        original_draft_id=row.original_draft_id,
        followup_rule_id=row.followup_rule_id,
        status=row.status,
        run_after=row.run_after,
        actor_user_id=row.actor_user_id,
        actor_role=row.actor_role,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class FollowUpRepository(BaseRepository):
    """Tenant-scoped repository for follow-up rules and schedules."""

    async def create_followup_rule(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        delay_seconds: int,
    ) -> FollowUpRuleRecord:
        row = (
            (
                await self.conn.execute(
                    insert(FollowUpRule)
                    .values(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        delay_seconds=delay_seconds,
                    )
                    .returning(FollowUpRule)
                )
            )
            .scalars()
            .one()
        )
        return _rule(row)

    async def list_followup_rules(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[FollowUpRuleRecord], str | None]:
        stmt = select(FollowUpRule).where(FollowUpRule.tenant_id == tenant_id)
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                return [], None
            cursor_row = (
                (
                    await self.conn.execute(
                        select(FollowUpRule).where(
                            FollowUpRule.tenant_id == tenant_id,
                            FollowUpRule.id == cursor_id,
                        )
                    )
                )
                .scalars()
                .first()
            )
            if cursor_row is None:
                return [], None
            stmt = stmt.where(
                or_(
                    FollowUpRule.created_at < cursor_row.created_at,
                    and_(
                        FollowUpRule.created_at == cursor_row.created_at,
                        FollowUpRule.id < cursor_row.id,
                    ),
                )
            )
        rows = (
            (
                await self.conn.execute(
                    stmt.order_by(FollowUpRule.created_at.desc(), FollowUpRule.id.desc()).limit(
                        limit + 1
                    )
                )
            )
            .scalars()
            .all()
        )
        page_rows = rows[:limit]
        next_cursor = str(page_rows[-1].id) if len(rows) > limit and page_rows else None
        return [_rule(row) for row in page_rows], next_cursor

    async def get_followup_rule_by_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> FollowUpRuleRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(FollowUpRule).where(
                        FollowUpRule.tenant_id == tenant_id,
                        FollowUpRule.campaign_id == campaign_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _rule(row) if row is not None else None

    async def create_followup_schedule(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        original_outbound_message_id: uuid.UUID,
        original_draft_id: uuid.UUID,
        followup_rule_id: uuid.UUID,
        status: str,
        run_after: datetime,
        actor_user_id: uuid.UUID,
        actor_role: str,
    ) -> FollowUpScheduleRecord:
        row = (
            (
                await self.conn.execute(
                    insert(FollowUpSchedule)
                    .values(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        contact_id=contact_id,
                        original_outbound_message_id=original_outbound_message_id,
                        original_draft_id=original_draft_id,
                        followup_rule_id=followup_rule_id,
                        status=status,
                        run_after=run_after,
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                    )
                    .returning(FollowUpSchedule)
                )
            )
            .scalars()
            .one()
        )
        return _schedule(row)

    async def get_followup_schedule(
        self, *, tenant_id: uuid.UUID, schedule_id: uuid.UUID
    ) -> FollowUpScheduleRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(FollowUpSchedule).where(
                        FollowUpSchedule.tenant_id == tenant_id,
                        FollowUpSchedule.id == schedule_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _schedule(row) if row is not None else None

    async def get_followup_schedule_by_original_message(
        self, *, tenant_id: uuid.UUID, original_outbound_message_id: uuid.UUID
    ) -> FollowUpScheduleRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(FollowUpSchedule).where(
                        FollowUpSchedule.tenant_id == tenant_id,
                        FollowUpSchedule.original_outbound_message_id
                        == original_outbound_message_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _schedule(row) if row is not None else None

    async def list_followup_schedules(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[FollowUpScheduleRecord], str | None]:
        stmt = select(FollowUpSchedule).where(FollowUpSchedule.tenant_id == tenant_id)
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                return [], None
            cursor_row = (
                (
                    await self.conn.execute(
                        select(FollowUpSchedule).where(
                            FollowUpSchedule.tenant_id == tenant_id,
                            FollowUpSchedule.id == cursor_id,
                        )
                    )
                )
                .scalars()
                .first()
            )
            if cursor_row is None:
                return [], None
            stmt = stmt.where(
                or_(
                    FollowUpSchedule.created_at < cursor_row.created_at,
                    and_(
                        FollowUpSchedule.created_at == cursor_row.created_at,
                        FollowUpSchedule.id < cursor_row.id,
                    ),
                )
            )
        rows = (
            (
                await self.conn.execute(
                    stmt.order_by(
                        FollowUpSchedule.created_at.desc(),
                        FollowUpSchedule.id.desc(),
                    ).limit(limit + 1)
                )
            )
            .scalars()
            .all()
        )
        page_rows = rows[:limit]
        next_cursor = str(page_rows[-1].id) if len(rows) > limit and page_rows else None
        return [_schedule(row) for row in page_rows], next_cursor

    async def update_followup_schedule_status(
        self,
        *,
        tenant_id: uuid.UUID,
        schedule_id: uuid.UUID,
        status: str,
    ) -> FollowUpScheduleRecord | None:
        from sqlalchemy import text

        values: dict[str, Any] = {"status": status, "updated_at": text("now()")}
        row = (
            (
                await self.conn.execute(
                    update(FollowUpSchedule)
                    .where(
                        FollowUpSchedule.tenant_id == tenant_id,
                        FollowUpSchedule.id == schedule_id,
                    )
                    .values(**values)
                    .returning(FollowUpSchedule)
                )
            )
            .scalars()
            .first()
        )
        return _schedule(row) if row is not None else None
