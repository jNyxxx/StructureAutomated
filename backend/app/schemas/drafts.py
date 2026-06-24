"""Safe draft API schemas for Phase 2 P2-3."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.repositories.draft_repo import DraftEvidenceRecord, DraftRecord
from app.schemas.pagination import PageInfo
from app.services.draft_generation import DraftCreateResult
from app.services.draft_read import DraftEvidencePage


class DraftGenerateRequest(BaseModel):
    campaign_id: uuid.UUID
    contact_id: uuid.UUID


class DraftDTO(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str
    subject: str
    body: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: DraftRecord) -> DraftDTO:
        return cls(
            id=record.id,
            campaign_id=record.campaign_id,
            contact_id=record.contact_id,
            status=record.status,
            subject=record.subject,
            body=record.body,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class DraftGenerateResponse(BaseModel):
    draft: DraftDTO | None = None
    idempotency_replay: bool = False

    @classmethod
    def from_result(cls, result: DraftCreateResult) -> DraftGenerateResponse:
        return cls(
            draft=DraftDTO.from_record(result.draft) if result.draft else None,
            idempotency_replay=result.idempotency_replay,
        )


class DraftDetailResponse(BaseModel):
    draft: DraftDTO

    @classmethod
    def from_record(cls, record: DraftRecord) -> DraftDetailResponse:
        return cls(draft=DraftDTO.from_record(record))


class DraftEvidenceDTO(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    content_snippet: str
    created_at: datetime

    @classmethod
    def from_record(cls, record: DraftEvidenceRecord) -> DraftEvidenceDTO:
        return cls(
            id=record.id,
            draft_id=record.draft_id,
            source_type=record.source_type,
            source_id=record.source_id,
            content_snippet=record.content_snippet,
            created_at=record.created_at,
        )


class DraftEvidenceListResponse(BaseModel):
    evidence: list[DraftEvidenceDTO]
    page: PageInfo

    @classmethod
    def from_page(cls, page: DraftEvidencePage) -> DraftEvidenceListResponse:
        return cls(
            evidence=[DraftEvidenceDTO.from_record(item) for item in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )
