"""Repository for human review queue items."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update

from app.models.review import ReviewItem
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class ReviewRecord:
    """Read-only representation of a ReviewItem."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    draft_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str
    reviewer_user_id: uuid.UUID | None
    action_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _review_item(row: ReviewItem) -> ReviewRecord:
    return ReviewRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        draft_id=row.draft_id,
        campaign_id=row.campaign_id,
        contact_id=row.contact_id,
        status=row.status,
        reviewer_user_id=row.reviewer_user_id,
        action_reason=row.action_reason,
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ReviewRepository(BaseRepository):
    """Tenant-scoped repository for human review queue items."""

    async def create_review_item(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str = "pending_review",
    ) -> ReviewRecord:
        row = (
            (
                await self.conn.execute(
                    insert(ReviewItem)
                    .values(
                        tenant_id=tenant_id,
                        draft_id=draft_id,
                        campaign_id=campaign_id,
                        contact_id=contact_id,
                        status=status,
                    )
                    .returning(ReviewItem)
                )
            )
            .scalars()
            .one()
        )
        return _review_item(row)

    async def get_review_item(
        self, *, tenant_id: uuid.UUID, review_id: uuid.UUID
    ) -> ReviewRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(ReviewItem).where(
                        ReviewItem.tenant_id == tenant_id,
                        ReviewItem.id == review_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _review_item(row) if row is not None else None

    async def get_review_item_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> ReviewRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(ReviewItem).where(
                        ReviewItem.tenant_id == tenant_id,
                        ReviewItem.draft_id == draft_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _review_item(row) if row is not None else None

    async def update_review_status(
        self,
        *,
        tenant_id: uuid.UUID,
        review_id: uuid.UUID,
        status: str,
        reviewer_user_id: uuid.UUID | None = None,
        action_reason: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> ReviewRecord | None:
        values: dict[str, Any] = {"status": status}
        if reviewer_user_id is not None:
            values["reviewer_user_id"] = reviewer_user_id
        if action_reason is not None:
            values["action_reason"] = action_reason
        if reviewed_at is not None:
            values["reviewed_at"] = reviewed_at

        from sqlalchemy import text

        values["updated_at"] = text("now()")

        row = (
            (
                await self.conn.execute(
                    update(ReviewItem)
                    .where(
                        ReviewItem.tenant_id == tenant_id,
                        ReviewItem.id == review_id,
                    )
                    .values(**values)
                    .returning(ReviewItem)
                )
            )
            .scalars()
            .first()
        )
        return _review_item(row) if row is not None else None

    async def list_review_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[ReviewRecord]:
        stmt = select(ReviewItem).where(ReviewItem.tenant_id == tenant_id)
        if campaign_id is not None:
            stmt = stmt.where(ReviewItem.campaign_id == campaign_id)
        if status is not None:
            stmt = stmt.where(ReviewItem.status == status)

        stmt = stmt.order_by(ReviewItem.created_at.desc())
        rows = (await self.conn.execute(stmt)).scalars().all()
        return [_review_item(r) for r in rows]
