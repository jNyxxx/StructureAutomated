"""Read-only draft access service for Phase 2 draft/review APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.draft_repo import DraftEvidenceRecord, DraftRecord
from app.services.authz import (
    CAN_REVIEW_DRAFT,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)


@dataclass(frozen=True)
class DraftEvidencePage:
    items: tuple[DraftEvidenceRecord, ...]
    next_cursor: str | None
    limit: int


class DraftReadStore(Protocol):
    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> DraftRecord | None:
        """Return a tenant draft."""

    async def list_evidence_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> list[DraftEvidenceRecord]:
        """Return draft evidence rows."""


def _obj(record: DraftRecord | None) -> TenantOwnedObject | None:
    if record is None:
        return None
    return TenantOwnedObject(id=record.id, tenant_id=record.tenant_id)


class DraftReadService:
    """Safe read service for drafts and evidence."""

    def __init__(
        self,
        *,
        store: DraftReadStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
    ) -> None:
        self._store = store
        self._rbac = rbac
        self._object_authz = object_authz

    async def get_draft(self, *, principal: CurrentPrincipal, draft_id: uuid.UUID) -> DraftRecord:
        self._rbac.require(principal, CAN_REVIEW_DRAFT)
        draft = await self._store.get_draft(tenant_id=principal.tenant_id, draft_id=draft_id)
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(draft))
        if draft is None:
            raise AppError("DRAFT_NOT_FOUND", "Draft not found.", status_code=404)
        return draft

    async def list_evidence(
        self,
        *,
        principal: CurrentPrincipal,
        draft_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> DraftEvidencePage:
        draft = await self.get_draft(principal=principal, draft_id=draft_id)
        evidence = await self._store.list_evidence_for_draft(
            tenant_id=principal.tenant_id, draft_id=draft.id
        )
        start = 0
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                return DraftEvidencePage(items=(), next_cursor=None, limit=limit)
            ids = [item.id for item in evidence]
            if cursor_id not in ids:
                return DraftEvidencePage(items=(), next_cursor=None, limit=limit)
            start = ids.index(cursor_id) + 1
        window = evidence[start : start + limit + 1]
        items = tuple(window[:limit])
        next_cursor = str(items[-1].id) if len(window) > limit and items else None
        return DraftEvidencePage(items=items, next_cursor=next_cursor, limit=limit)
