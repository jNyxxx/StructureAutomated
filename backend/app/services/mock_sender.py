"""Mock email sending service for Phase 1 Slice P1-09."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.email_provider import (
    EmailSendProvider,
    MockEmailSendProvider,
    ProviderSendRequest,
)
from app.services.idempotency import IdempotencyOutcome, IdempotencyState
from app.services.send_gate import SendGateService


class SendingStore(Protocol):
    async def create_outbound_message(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        sent_at: datetime | None = None,
    ) -> Any:
        """Create outbound message."""


class IdempotencyGate(Protocol):
    async def begin(
        self,
        *,
        key: str,
        request_payload: Any,
        now: datetime,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> IdempotencyOutcome:
        """Begin an idempotent operation."""

    async def complete(
        self,
        *,
        key: str,
        response_payload: Any,
        status_code: int,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        """Complete an idempotent operation."""


@dataclass(frozen=True)
class MockSendResult:
    """Production-shaped result of mock sending operation."""

    outbound_message_id: uuid.UUID
    status: str
    sent_at: datetime | None
    mock_only: bool = True


@dataclass(frozen=True)
class MockSendIntentResult:
    result: MockSendResult | None
    idempotency_replay: bool = False
    mock_only: bool = True


class MockSenderService:
    """Service simulating email transmission with safety send gates enforced."""

    def __init__(
        self,
        *,
        sending_store: SendingStore,
        send_gate: SendGateService,
        followups: Any = None,
        idempotency: IdempotencyGate | None = None,
        audit_record: Any = None,
        email_provider: EmailSendProvider | None = None,
    ) -> None:
        self._sending_store = sending_store
        self._send_gate = send_gate
        self._followups = followups
        self._idempotency = idempotency
        self._audit_record = audit_record
        self._email_provider = email_provider or MockEmailSendProvider()

    async def send_approved_draft_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        draft_id: uuid.UUID,
        idempotency_key: str | None,
        now: datetime,
    ) -> MockSendIntentResult:
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "draft_id": str(draft_id),
            "action": "mock_send_intent",
            "mock_only": True,
        }
        if self._idempotency is not None and idempotency_key is not None:
            outcome = await self._idempotency.begin(
                key=idempotency_key,
                request_payload=request_payload,
                now=now,
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
            if outcome.is_replay:
                return MockSendIntentResult(result=None, idempotency_replay=True)
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "MOCK_SEND_INTENT_IN_PROGRESS",
                    "Mock send intent is already in progress.",
                    status_code=409,
                )

        result = await self.send_approved_draft(principal=principal, draft_id=draft_id, now=now)

        if self._idempotency is not None and idempotency_key is not None:
            await self._idempotency.complete(
                key=idempotency_key,
                response_payload={
                    "draft_id": str(draft_id),
                    "outbound_message_id": str(result.outbound_message_id),
                    "status": result.status,
                    "mock_only": True,
                },
                status_code=201,
                tenant_id=principal.tenant_id,
            )
        return MockSendIntentResult(result=result)

    async def send_approved_draft(
        self,
        principal: CurrentPrincipal,
        *,
        draft_id: uuid.UUID,
        now: datetime,
    ) -> MockSendResult:
        """Evaluate gates and perform mock send of an approved draft email."""
        try:
            await self._send_gate.evaluate_gate(principal=principal, draft_id=draft_id, now=now)
        except AppError as e:
            if e.code == "DUPLICATE_SEND":
                raise

            # Record outbound message block to track attempt
            await self._sending_store.create_outbound_message(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="blocked",
            )
            await self._audit(
                event_type="outbound_message.blocked",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"error": e.code},
            )
            raise

        provider_result = await self._email_provider.send(
            ProviderSendRequest(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                idempotency_key=f"mock-send:{draft_id}",
                requested_at=now,
                recipient_ref=f"draft:{draft_id}:contact",
                content_ref=f"draft:{draft_id}:content",
                safe_metadata={"mock_only": "true"},
            )
        )
        if provider_result.provider_status != "accepted":
            blocked = await self._sending_store.create_outbound_message(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="blocked",
            )
            await self._audit(
                event_type="outbound_message.provider_failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="outbound_message",
                object_id=blocked.id,
                details={
                    "provider": provider_result.provider,
                    "provider_status": provider_result.provider_status,
                    "error_code": provider_result.error_code,
                },
            )
            raise AppError(
                "EMAIL_PROVIDER_SEND_FAILED",
                "Email provider send failed.",
                status_code=503,
                details={
                    "provider_status": provider_result.provider_status,
                    "error_code": provider_result.error_code,
                },
            )

        # Create successful mock sent outbound message
        msg = await self._sending_store.create_outbound_message(
            tenant_id=principal.tenant_id,
            draft_id=draft_id,
            status="mock_sent",
            sent_at=now,
        )

        # Audit event outbound_message.sent
        await self._audit(
            event_type="outbound_message.sent",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="outbound_message",
            object_id=msg.id,
            details={
                "draft_id": str(draft_id),
                "provider": provider_result.provider,
                "provider_status": provider_result.provider_status,
                "provider_message_id": provider_result.provider_message_id,
            },
        )

        # Auto-schedule follow-up checkups if rule exists
        if self._followups is not None:
            await self._followups.schedule_followup(
                principal=principal,
                draft_id=draft_id,
                outbound_message_id=msg.id,
                now=now,
            )

        return MockSendResult(
            outbound_message_id=msg.id,
            status=msg.status,
            sent_at=msg.sent_at,
        )

    async def _audit(
        self,
        *,
        event_type: str,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        object_type: str,
        object_id: uuid.UUID,
        details: dict[str, Any],
    ) -> None:
        if self._audit_record is not None:
            if callable(self._audit_record):
                await self._audit_record(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    object_type=object_type,
                    object_id=object_id,
                    details=details,
                )
            else:
                await self._audit_record.record(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    object_type=object_type,
                    object_id=object_id,
                    details=details,
                )
