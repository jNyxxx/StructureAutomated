"""Mock sender provider-boundary tests for P3-5b."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.sending_repo import OutboundMessageRecord
from app.services.email_provider import ProviderSendRequest, ProviderSendResult
from app.services.idempotency import IdempotencyOutcome, IdempotencyState
from app.services.mock_sender import MockSenderService

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_DRAFT = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_NOW = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)


def _principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=_ACTOR,
        email="owner@example.com",
        tenant_id=_TENANT,
        role="owner",
        membership_version=1,
        mfa_verified=True,
    )


class _SendingStore:
    def __init__(self) -> None:
        self.messages: list[OutboundMessageRecord] = []

    async def create_outbound_message(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        sent_at: datetime | None = None,
    ) -> OutboundMessageRecord:
        row = OutboundMessageRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            draft_id=draft_id,
            status=status,
            sent_at=sent_at,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.messages.append(row)
        return row


class _SendGate:
    def __init__(self, *, error: AppError | None = None) -> None:
        self.error = error
        self.calls = 0

    async def evaluate_gate(
        self, *, principal: CurrentPrincipal, draft_id: uuid.UUID, now: datetime
    ) -> None:
        self.calls += 1
        if self.error is not None:
            raise self.error


class _Provider:
    kind = "mock"

    def __init__(self, result: ProviderSendResult | None = None) -> None:
        self.result = result or ProviderSendResult(
            provider="mock",
            provider_message_id="mock-provider-message",
            provider_status="accepted",
            accepted_at=_NOW,
        )
        self.calls: list[ProviderSendRequest] = []

    async def send(self, message: ProviderSendRequest) -> ProviderSendResult:
        self.calls.append(message)
        return self.result


class _IdempotencyReplay:
    async def begin(self, **kwargs: Any) -> IdempotencyOutcome:
        return IdempotencyOutcome(IdempotencyState.REPLAY, status_code=201)

    async def complete(self, **kwargs: Any) -> None:
        raise AssertionError("replay must not complete or send")


async def test_provider_send_happens_only_after_gate_passes() -> None:
    store = _SendingStore()
    gate = _SendGate()
    provider = _Provider()
    sender = MockSenderService(sending_store=store, send_gate=gate, email_provider=provider)

    result = await sender.send_approved_draft(_principal(), draft_id=_DRAFT, now=_NOW)

    assert gate.calls == 1
    assert len(provider.calls) == 1
    assert provider.calls[0].tenant_id == _TENANT
    assert provider.calls[0].draft_id == _DRAFT
    assert provider.calls[0].recipient_ref == f"draft:{_DRAFT}:contact"
    assert provider.calls[0].content_ref == f"draft:{_DRAFT}:content"
    assert result.status == "mock_sent"
    assert store.messages[0].status == "mock_sent"


async def test_gate_failure_blocks_before_provider_send() -> None:
    store = _SendingStore()
    gate = _SendGate(
        error=AppError("REVIEW_NOT_APPROVED", "Draft has not been reviewed.", status_code=400)
    )
    provider = _Provider()
    audits: list[dict[str, Any]] = []

    async def _audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    sender = MockSenderService(
        sending_store=store,
        send_gate=gate,
        email_provider=provider,
        audit_record=_audit,
    )

    with pytest.raises(AppError) as excinfo:
        await sender.send_approved_draft(_principal(), draft_id=_DRAFT, now=_NOW)

    assert excinfo.value.code == "REVIEW_NOT_APPROVED"
    assert provider.calls == []
    assert store.messages[0].status == "blocked"
    assert audits[0]["details"] == {"error": "REVIEW_NOT_APPROVED"}


async def test_provider_failure_records_safe_blocked_state() -> None:
    store = _SendingStore()
    provider = _Provider(
        ProviderSendResult(
            provider="mock",
            provider_message_id=None,
            provider_status="failed",
            error_code="SAFE_PROVIDER_FAILURE",
            error_message="Safe failure only.",
        )
    )
    audits: list[dict[str, Any]] = []

    async def _audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    sender = MockSenderService(
        sending_store=store,
        send_gate=_SendGate(),
        email_provider=provider,
        audit_record=_audit,
    )

    with pytest.raises(AppError) as excinfo:
        await sender.send_approved_draft(_principal(), draft_id=_DRAFT, now=_NOW)

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.code == "EMAIL_PROVIDER_SEND_FAILED"
    assert exc.details == {
        "provider_status": "failed",
        "error_code": "SAFE_PROVIDER_FAILURE",
    }
    assert store.messages[0].status == "blocked"
    assert audits[0]["event_type"] == "outbound_message.provider_failed"
    assert audits[0]["details"] == {
        "provider": "mock",
        "provider_status": "failed",
        "error_code": "SAFE_PROVIDER_FAILURE",
    }
    serialized = repr(exc.details) + repr(audits)
    assert "CHANGE_ME" not in serialized
    assert "sk_live" not in serialized
    assert "prospect@example.com" not in serialized


async def test_idempotency_replay_prevents_provider_send() -> None:
    store = _SendingStore()
    gate = _SendGate()
    provider = _Provider()
    sender = MockSenderService(
        sending_store=store,
        send_gate=gate,
        email_provider=provider,
        idempotency=_IdempotencyReplay(),
    )

    result = await sender.send_approved_draft_idempotent(
        _principal(), draft_id=_DRAFT, idempotency_key="send-key", now=_NOW
    )

    assert result.idempotency_replay is True
    assert result.result is None
    assert gate.calls == 0
    assert provider.calls == []
    assert store.messages == []
