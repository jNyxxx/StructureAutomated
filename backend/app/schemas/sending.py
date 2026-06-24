"""Safe mock/local sending API schemas for Phase 2 P2-4."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.repositories.sending_repo import OutboundMessageRecord, SendGateResultRecord
from app.schemas.pagination import PageInfo
from app.services.mock_sender import MockSendIntentResult
from app.services.outbound_read import OutboundMessagePage
from app.services.send_gate import SendGateDryRunResult


class SendGateDryRunRequest(BaseModel):
    draft_id: uuid.UUID


class SendIntentRequest(BaseModel):
    draft_id: uuid.UUID


class SendGateResultDTO(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    status: str
    deny_reason_code: str | None = None
    created_at: datetime
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: SendGateResultRecord) -> SendGateResultDTO:
        return cls(
            id=record.id,
            draft_id=record.draft_id,
            status=record.status,
            deny_reason_code=record.deny_reason_code,
            created_at=record.created_at,
        )


class SendGateDryRunResponse(BaseModel):
    send_gate_result: SendGateResultDTO | None = None
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: SendGateDryRunResult) -> SendGateDryRunResponse:
        return cls(
            send_gate_result=(
                SendGateResultDTO.from_record(result.gate_result)
                if result.gate_result is not None
                else None
            ),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )


class MockSendResultDTO(BaseModel):
    outbound_message_id: uuid.UUID
    status: str
    sent_at: datetime | None = None
    mock_only: bool = True


class SendIntentResponse(BaseModel):
    result: MockSendResultDTO | None = None
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: MockSendIntentResult) -> SendIntentResponse:
        return cls(
            result=(
                MockSendResultDTO(
                    outbound_message_id=result.result.outbound_message_id,
                    status=result.result.status,
                    sent_at=result.result.sent_at,
                    mock_only=result.result.mock_only,
                )
                if result.result is not None
                else None
            ),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )


class OutboundMessageDTO(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    status: str
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: OutboundMessageRecord) -> OutboundMessageDTO:
        return cls(
            id=record.id,
            draft_id=record.draft_id,
            status=record.status,
            sent_at=record.sent_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class OutboundMessageListResponse(BaseModel):
    outbound_messages: list[OutboundMessageDTO]
    page: PageInfo
    mock_only: bool = True

    @classmethod
    def from_page(cls, page: OutboundMessagePage) -> OutboundMessageListResponse:
        return cls(
            outbound_messages=[OutboundMessageDTO.from_record(item) for item in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )


class OutboundMessageDetailResponse(BaseModel):
    outbound_message: OutboundMessageDTO
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: OutboundMessageRecord) -> OutboundMessageDetailResponse:
        return cls(outbound_message=OutboundMessageDTO.from_record(record))
