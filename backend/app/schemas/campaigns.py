"""Safe request/response schemas for the Phase 2 campaign API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.pagination import PageInfo
from app.services.campaign import (
    CampaignContactRecord,
    CampaignContactSelectionResult,
    CampaignCreateResult,
    CampaignRecord,
    CampaignUpdateResult,
)


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5_000)
    goal: str | None = Field(default=None, max_length=5_000)
    target_segment: str | None = Field(default=None, max_length=5_000)
    notes: str | None = Field(default=None, max_length=5_000)


class CampaignUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5_000)
    goal: str | None = Field(default=None, max_length=5_000)
    target_segment: str | None = Field(default=None, max_length=5_000)
    notes: str | None = Field(default=None, max_length=5_000)
    status: str | None = None


class CampaignContactSelectRequest(BaseModel):
    contact_id: uuid.UUID
    status: str = Field(default="selected", max_length=64)


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


class CampaignUpdateResponse(BaseModel):
    campaign: CampaignDTO | None = None
    idempotency_replay: bool = False

    @classmethod
    def from_result(cls, result: CampaignUpdateResult) -> CampaignUpdateResponse:
        return cls(
            campaign=(CampaignDTO.from_record(result.campaign) if result.campaign else None),
            idempotency_replay=result.idempotency_replay,
        )


class CampaignContactDTO(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str

    @classmethod
    def from_record(cls, record: CampaignContactRecord) -> CampaignContactDTO:
        return cls(
            id=record.id,
            campaign_id=record.campaign_id,
            contact_id=record.contact_id,
            status=record.status,
        )


class CampaignContactSelectionResponse(BaseModel):
    campaign_contact: CampaignContactDTO | None = None
    idempotency_replay: bool = False

    @classmethod
    def from_result(
        cls, result: CampaignContactSelectionResult
    ) -> CampaignContactSelectionResponse:
        return cls(
            campaign_contact=(
                CampaignContactDTO.from_record(result.campaign_contact)
                if result.campaign_contact
                else None
            ),
            idempotency_replay=result.idempotency_replay,
        )
