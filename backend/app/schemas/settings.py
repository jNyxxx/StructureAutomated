"""Safe tenant settings, team read, and audit read API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PageInfo
from app.services.settings_api import (
    AuditEventPage,
    AuditEventReadRecord,
    MembershipReadRecord,
    TenantSettingsRecord,
    TenantUpdateResult,
    safe_tenant_settings,
)


class TenantDTO(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: TenantSettingsRecord) -> TenantDTO:
        return cls(
            id=record.id,
            name=record.name,
            status=record.status,
            settings=safe_tenant_settings(record.settings),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class TenantResponse(BaseModel):
    tenant: TenantDTO
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: TenantSettingsRecord) -> TenantResponse:
        return cls(tenant=TenantDTO.from_record(record))


class TenantUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    settings: dict[str, Any] | None = None


class TenantUpdateResponse(BaseModel):
    tenant: TenantDTO
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: TenantUpdateResult) -> TenantUpdateResponse:
        return cls(
            tenant=TenantDTO.from_record(result.tenant),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )


class MembershipDTO(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    membership_version: int
    created_at: datetime
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: MembershipReadRecord) -> MembershipDTO:
        return cls(
            id=record.id,
            user_id=record.user_id,
            role=record.role,
            membership_version=record.membership_version,
            created_at=record.created_at,
        )


class MembershipListResponse(BaseModel):
    memberships: list[MembershipDTO]
    mock_only: bool = True

    @classmethod
    def from_records(cls, records: tuple[MembershipReadRecord, ...]) -> MembershipListResponse:
        return cls(memberships=[MembershipDTO.from_record(record) for record in records])


class AuditEventDTO(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_user_id: uuid.UUID | None = None
    object_type: str | None = None
    object_id: uuid.UUID | None = None
    request_id: str | None = None
    job_id: uuid.UUID | None = None
    redacted_details: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_record(cls, record: AuditEventReadRecord) -> AuditEventDTO:
        return cls(
            id=record.id,
            event_type=record.event_type,
            actor_user_id=record.actor_user_id,
            object_type=record.object_type,
            object_id=record.object_id,
            request_id=record.request_id,
            job_id=record.job_id,
            redacted_details=record.redacted_details,
            created_at=record.created_at,
        )


class AuditEventListResponse(BaseModel):
    audit_events: list[AuditEventDTO]
    page: PageInfo
    mock_only: bool = True

    @classmethod
    def from_page(cls, page: AuditEventPage) -> AuditEventListResponse:
        return cls(
            audit_events=[AuditEventDTO.from_record(record) for record in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )
