"""Read-only outbound message service for mock/local send APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.sending_repo import OutboundMessageRecord
from app.services.authz import CAN_REVIEW_DRAFT, CAN_SCHEDULE_SEND, RBACService


@dataclass(frozen=True)
class OutboundMessagePage:
    items: tuple[OutboundMessageRecord, ...]
    next_cursor: str | None
    limit: int


class OutboundReadStore(Protocol):
    async def list_outbound_messages(
        self, *, tenant_id: uuid.UUID, cursor: str | None, limit: int
    ) -> tuple[list[OutboundMessageRecord], str | None]:
        """List tenant outbound messages."""

    async def get_outbound_message_by_id(
        self, *, tenant_id: uuid.UUID, message_id: uuid.UUID
    ) -> OutboundMessageRecord | None:
        """Get one tenant outbound message."""


class OutboundReadService:
    """Safe read service for mock outbound messages."""

    def __init__(self, *, store: OutboundReadStore, rbac: RBACService) -> None:
        self._store = store
        self._rbac = rbac

    def _require_read(self, principal: CurrentPrincipal) -> None:
        if not (
            self._rbac.has_permission(principal.role, CAN_REVIEW_DRAFT)
            or self._rbac.has_permission(principal.role, CAN_SCHEDULE_SEND)
        ):
            raise AppError("FORBIDDEN", "Access denied.", status_code=403)

    async def list_messages(
        self, *, principal: CurrentPrincipal, cursor: str | None, limit: int
    ) -> OutboundMessagePage:
        self._require_read(principal)
        items, next_cursor = await self._store.list_outbound_messages(
            tenant_id=principal.tenant_id, cursor=cursor, limit=limit
        )
        return OutboundMessagePage(items=tuple(items), next_cursor=next_cursor, limit=limit)

    async def get_message(
        self, *, principal: CurrentPrincipal, message_id: uuid.UUID
    ) -> OutboundMessageRecord:
        self._require_read(principal)
        message = await self._store.get_outbound_message_by_id(
            tenant_id=principal.tenant_id, message_id=message_id
        )
        if message is None or message.tenant_id != principal.tenant_id:
            raise AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
        return message
