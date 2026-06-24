"""Safe mock/local compliance and suppression API schemas for Phase 2 P2-6."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.pagination import PageInfo
from app.services.compliance import ComplianceProfileRecord, SuppressionRecord
from app.services.compliance_api import ComplianceProfileActionResult, SuppressionActionResult


class ComplianceProfileDTO(BaseModel):
    jurisdiction: str
    sending_review_required: bool
    live_sending_allowed: bool
    sms_allowed: bool
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: ComplianceProfileRecord) -> ComplianceProfileDTO:
        return cls(
            jurisdiction=record.jurisdiction,
            sending_review_required=record.sending_review_required,
            live_sending_allowed=record.live_sending_allowed,
            sms_allowed=record.sms_allowed,
        )


class ComplianceProfileResponse(BaseModel):
    compliance_profile: ComplianceProfileDTO
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: ComplianceProfileRecord) -> ComplianceProfileResponse:
        return cls(compliance_profile=ComplianceProfileDTO.from_record(record))


class ComplianceProfileUpdateRequest(BaseModel):
    jurisdiction: str = Field(default="US", max_length=50)
    sending_review_required: bool = True
    live_sending_allowed: bool = False
    sms_allowed: bool = False


class ComplianceProfileActionResponse(BaseModel):
    compliance_profile: ComplianceProfileDTO
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: ComplianceProfileActionResult) -> ComplianceProfileActionResponse:
        return cls(
            compliance_profile=ComplianceProfileDTO.from_record(result.profile),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )


class SuppressionDTO(BaseModel):
    id: uuid.UUID
    channel: str
    reason: str
    source: str
    never_contact: bool
    created_at: datetime
    revoked_at: datetime | None = None
    active: bool
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: SuppressionRecord) -> SuppressionDTO:
        return cls(
            id=record.id,
            channel=record.channel,
            reason=record.reason,
            source=record.source,
            never_contact=record.never_contact,
            created_at=record.created_at,
            revoked_at=record.revoked_at,
            active=record.is_active(),
        )


class SuppressionListResponse(BaseModel):
    suppressions: list[SuppressionDTO]
    page: PageInfo
    mock_only: bool = True


class SuppressionCreateRequest(BaseModel):
    channel: str = Field(default="email", max_length=50)
    contact_identifier: str = Field(min_length=1, max_length=320)
    reason: str = Field(min_length=1, max_length=500)
    source: str = Field(default="manual", min_length=1, max_length=100)
    never_contact: bool = True


class SuppressionActionResponse(BaseModel):
    suppression: SuppressionDTO
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: SuppressionActionResult) -> SuppressionActionResponse:
        return cls(
            suppression=SuppressionDTO.from_record(result.suppression),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )
