"""Read-only contacts/prospects service for Phase 2 P2-1b.

No Prospect table exists yet. The prospects read path is intentionally a safe
projection over tenant contacts, so frontend wiring can start later without
creating new persistence or write behavior in this slice.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from app.auth.principal import CurrentPrincipal
from app.schemas.pagination import PageParams
from app.services.authz import (
    CAN_READ_DASHBOARD,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)


@dataclass(frozen=True)
class ContactReadRecord:
    """Safe contact fields for API read DTOs."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str | None
    title: str | None
    email: str | None
    domain: str | None
    company_name: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ContactReadPage:
    """Tenant-scoped cursor page of contact read records."""

    items: tuple[ContactReadRecord, ...]
    next_cursor: str | None
    limit: int


class ContactReadStore(Protocol):
    async def list_contacts(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> ContactReadPage:
        """List tenant contacts using an opaque cursor and clamped limit."""

    async def get_contact_by_id(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ContactReadRecord | None:
        """Return one tenant contact, if visible under tenant scope."""


class ContactReadService:
    """Thin read-only service for contacts and contact-backed prospects."""

    def __init__(
        self,
        *,
        store: ContactReadStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
    ) -> None:
        self._store = store
        self._rbac = rbac
        self._object_authz = object_authz

    async def list_contacts(
        self, *, principal: CurrentPrincipal, page: PageParams
    ) -> ContactReadPage:
        """List tenant contacts. Requires the existing read/dashboard permission."""
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        return await self._store.list_contacts(
            tenant_id=principal.tenant_id,
            cursor=page.cursor,
            limit=page.limit,
        )

    async def list_prospects(
        self, *, principal: CurrentPrincipal, page: PageParams
    ) -> ContactReadPage:
        """Return the current prospect projection over tenant contacts."""
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        return await self._store.list_contacts(
            tenant_id=principal.tenant_id,
            cursor=page.cursor,
            limit=page.limit,
        )

    async def get_contact(
        self, *, principal: CurrentPrincipal, contact_id: uuid.UUID
    ) -> ContactReadRecord:
        """Return one tenant contact or fail closed with object-access policy."""
        self._rbac.require(principal, CAN_READ_DASHBOARD)
        contact = await self._store.get_contact_by_id(
            tenant_id=principal.tenant_id, contact_id=contact_id
        )
        obj = (
            TenantOwnedObject(id=contact.id, tenant_id=contact.tenant_id)
            if contact is not None
            else None
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=obj)
        return cast(ContactReadRecord, contact)
