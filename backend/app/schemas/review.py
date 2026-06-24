"""Safe review queue API schemas for Phase 2 P2-3."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.repositories.review_repo import ReviewRecord
from app.schemas.pagination import PageInfo
from app.services.review import ReviewActionResult
from app.services.review_read import ReviewItemPage


class ReviewItemDTO(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str
    reviewer_user_id: uuid.UUID | None = None
    action_reason: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: ReviewRecord) -> ReviewItemDTO:
        return cls(
            id=record.id,
            draft_id=record.draft_id,
            campaign_id=record.campaign_id,
            contact_id=record.contact_id,
            status=record.status,
            reviewer_user_id=record.reviewer_user_id,
            action_reason=record.action_reason,
            reviewed_at=record.reviewed_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ReviewItemListResponse(BaseModel):
    review_items: list[ReviewItemDTO]
    page: PageInfo

    @classmethod
    def from_page(cls, page: ReviewItemPage) -> ReviewItemListResponse:
        return cls(
            review_items=[ReviewItemDTO.from_record(item) for item in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )


class ReviewItemDetailResponse(BaseModel):
    review_item: ReviewItemDTO

    @classmethod
    def from_record(cls, record: ReviewRecord) -> ReviewItemDetailResponse:
        return cls(review_item=ReviewItemDTO.from_record(record))


class ReviewActionRequest(BaseModel):
    reason: str | None = None


class ReviewActionResponse(BaseModel):
    review_item: ReviewItemDTO | None = None
    idempotency_replay: bool = False

    @classmethod
    def from_result(cls, result: ReviewActionResult) -> ReviewActionResponse:
        return cls(
            review_item=(
                ReviewItemDTO.from_record(result.review_item)
                if result.review_item is not None
                else None
            ),
            idempotency_replay=result.idempotency_replay,
        )
