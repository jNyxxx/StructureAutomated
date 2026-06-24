"""Read-only human review queue service for Phase 2 APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.review_repo import ReviewRecord
from app.services.authz import (
    CAN_REVIEW_DRAFT,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)


@dataclass(frozen=True)
class ReviewItemPage:
    items: tuple[ReviewRecord, ...]
    next_cursor: str | None
    limit: int


class ReviewReadStore(Protocol):
    async def get_review_item(
        self, *, tenant_id: uuid.UUID, review_id: uuid.UUID
    ) -> ReviewRecord | None:
        """Return a tenant review item."""

    async def list_review_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[ReviewRecord]:
        """List tenant review items."""


def _obj(record: ReviewRecord | None) -> TenantOwnedObject | None:
    if record is None:
        return None
    return TenantOwnedObject(id=record.id, tenant_id=record.tenant_id)


class ReviewReadService:
    """Safe read service for the human review queue."""

    def __init__(
        self,
        *,
        store: ReviewReadStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
    ) -> None:
        self._store = store
        self._rbac = rbac
        self._object_authz = object_authz

    async def get_item(self, *, principal: CurrentPrincipal, review_id: uuid.UUID) -> ReviewRecord:
        self._rbac.require(principal, CAN_REVIEW_DRAFT)
        item = await self._store.get_review_item(tenant_id=principal.tenant_id, review_id=review_id)
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(item))
        if item is None:
            raise AppError("REVIEW_ITEM_NOT_FOUND", "Review item not found.", status_code=404)
        return item

    async def list_items(
        self,
        *,
        principal: CurrentPrincipal,
        cursor: str | None,
        limit: int,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> ReviewItemPage:
        self._rbac.require(principal, CAN_REVIEW_DRAFT)
        records = await self._store.list_review_queue(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            status=status,
        )
        start = 0
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                return ReviewItemPage(items=(), next_cursor=None, limit=limit)
            ids = [item.id for item in records]
            if cursor_id not in ids:
                return ReviewItemPage(items=(), next_cursor=None, limit=limit)
            start = ids.index(cursor_id) + 1
        window = records[start : start + limit + 1]
        items = tuple(window[:limit])
        next_cursor = str(items[-1].id) if len(window) > limit and items else None
        return ReviewItemPage(items=items, next_cursor=next_cursor, limit=limit)
