"""Mock email sending service for Phase 1 Slice P1-09."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
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


@dataclass(frozen=True)
class MockSendResult:
    """Production-shaped result of mock sending operation."""

    outbound_message_id: uuid.UUID
    status: str
    sent_at: datetime | None


class MockSenderService:
    """Service simulating email transmission with safety send gates enforced."""

    def __init__(
        self,
        *,
        sending_store: SendingStore,
        send_gate: SendGateService,
        audit_record: Any = None,
    ) -> None:
        self._sending_store = sending_store
        self._send_gate = send_gate
        self._audit_record = audit_record

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
            details={"draft_id": str(draft_id)},
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
