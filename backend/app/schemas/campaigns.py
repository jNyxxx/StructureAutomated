"""Safe request/response schemas for the Phase 2 campaign API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.pagination import PageInfo
from app.services.campaign import CampaignCreateResult, CampaignRecord


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5_000)
    goal: str | None = Field(default=None, max_length=5_000)
    target_segment: str | None = Field(default=None, max_length=5_000)
    notes: str | None = Field(default=None, max_length=5_000)


class CampaignDTO(BaseModel):
    id: uuid.UUID
    created_by_user_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    goal: str | None = None
    target_segment: str | None = None
    notes: str | None = None
    status: str

    @classmethod
    def from_record(cls, record: CampaignRecord) -> CampaignDTO:
        return cls(
            id=record.id,
            created_by_user_id=record.created_by_user_id,
            name=record.name,
            description=record.description,
            goal=record.goal,
            target_segment=record.target_segment,
            notes=record.notes,
            status=record.status,
        )


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignDTO]
    page: PageInfo


class CampaignDetailResponse(BaseModel):
    campaign: CampaignDTO

    @classmethod
    def from_record(cls, record: CampaignRecord) -> CampaignDetailResponse:
        return cls(campaign=CampaignDTO.from_record(record))


class CampaignCreateResponse(BaseModel):
    campaign: CampaignDTO | None = None
    idempotency_replay: bool = False

    @classmethod
    def from_result(cls, result: CampaignCreateResult) -> CampaignCreateResponse:
        return cls(
            campaign=(CampaignDTO.from_record(result.campaign) if result.campaign else None),
            idempotency_replay=result.idempotency_replay,
        )
