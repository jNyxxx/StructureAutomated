"""Safe mock/local follow-up API schemas for Phase 2 P2-4b."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.repositories.followup_repo import FollowUpRuleRecord, FollowUpScheduleRecord
from app.schemas.pagination import PageInfo
from app.services.followup_scheduler import (
    FollowUpActionResult,
    FollowUpRulePage,
    FollowUpSchedulePage,
)


class FollowUpRuleCreateRequest(BaseModel):
    campaign_id: uuid.UUID
    delay_seconds: int = Field(gt=0)


class FollowUpScheduleCreateRequest(BaseModel):
    original_outbound_message_id: uuid.UUID


class FollowUpRuleDTO(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    delay_seconds: int
    created_at: datetime
    updated_at: datetime
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: FollowUpRuleRecord) -> FollowUpRuleDTO:
        return cls(
            id=record.id,
            campaign_id=record.campaign_id,
            delay_seconds=record.delay_seconds,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class FollowUpScheduleDTO(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    original_outbound_message_id: uuid.UUID
    original_draft_id: uuid.UUID
    followup_rule_id: uuid.UUID
    status: str
    run_after: datetime
    created_at: datetime
    updated_at: datetime
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: FollowUpScheduleRecord) -> FollowUpScheduleDTO:
        return cls(
            id=record.id,
            campaign_id=record.campaign_id,
            contact_id=record.contact_id,
            original_outbound_message_id=record.original_outbound_message_id,
            original_draft_id=record.original_draft_id,
            followup_rule_id=record.followup_rule_id,
            status=record.status,
            run_after=record.run_after,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class FollowUpRuleListResponse(BaseModel):
    followup_rules: list[FollowUpRuleDTO]
    page: PageInfo
    mock_only: bool = True

    @classmethod
    def from_page(cls, page: FollowUpRulePage) -> FollowUpRuleListResponse:
        return cls(
            followup_rules=[FollowUpRuleDTO.from_record(item) for item in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )


class FollowUpRuleActionResponse(BaseModel):
    followup_rule: FollowUpRuleDTO | None = None
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: FollowUpActionResult) -> FollowUpRuleActionResponse:
        return cls(
            followup_rule=(
                FollowUpRuleDTO.from_record(result.record) if result.record is not None else None
            ),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )


class FollowUpScheduleListResponse(BaseModel):
    followup_schedules: list[FollowUpScheduleDTO]
    page: PageInfo
    mock_only: bool = True

    @classmethod
    def from_page(cls, page: FollowUpSchedulePage) -> FollowUpScheduleListResponse:
        return cls(
            followup_schedules=[FollowUpScheduleDTO.from_record(item) for item in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )


class FollowUpScheduleActionResponse(BaseModel):
    followup_schedule: FollowUpScheduleDTO | None = None
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: FollowUpActionResult) -> FollowUpScheduleActionResponse:
        return cls(
            followup_schedule=(
                FollowUpScheduleDTO.from_record(result.record)
                if result.record is not None
                else None
            ),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )
