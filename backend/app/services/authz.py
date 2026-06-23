"""Central RBAC, object-authorization, and support-access services (Slice 15)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError

Permission = str

CAN_READ_DASHBOARD = "dashboard:read"
CAN_IMPORT_CONTACTS = "contacts:import"
CAN_CREATE_CAMPAIGN = "campaign:create"
CAN_RUN_CAMPAIGN = "campaign:run"
CAN_REVIEW_DRAFT = "draft:review"
CAN_APPROVE_DRAFT = "draft:approve"
CAN_SCHEDULE_SEND = "send:schedule"
CAN_MANAGE_TEAM = "team:manage"
CAN_MANAGE_BILLING = "billing:manage"
CAN_READ_AUDIT = "audit:read"
CAN_MANAGE_INTEGRATIONS = "integrations:manage"
CAN_GRANT_SUPPORT_ACCESS = "support_access:grant"
CAN_USE_SUPPORT_ACCESS = "support_access:use"
CAN_MANAGE_KNOWLEDGE = "knowledge:manage"
CAN_CREATE_DRAFT = "draft:create"

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "owner": frozenset(
        {
            CAN_READ_DASHBOARD,
            CAN_IMPORT_CONTACTS,
            CAN_CREATE_CAMPAIGN,
            CAN_RUN_CAMPAIGN,
            CAN_REVIEW_DRAFT,
            CAN_APPROVE_DRAFT,
            CAN_SCHEDULE_SEND,
            CAN_MANAGE_TEAM,
            CAN_MANAGE_BILLING,
            CAN_READ_AUDIT,
            CAN_MANAGE_INTEGRATIONS,
            CAN_GRANT_SUPPORT_ACCESS,
            CAN_MANAGE_KNOWLEDGE,
            CAN_CREATE_DRAFT,
        }
    ),
    "admin": frozenset(
        {
            CAN_READ_DASHBOARD,
            CAN_IMPORT_CONTACTS,
            CAN_CREATE_CAMPAIGN,
            CAN_RUN_CAMPAIGN,
            CAN_REVIEW_DRAFT,
            CAN_APPROVE_DRAFT,
            CAN_SCHEDULE_SEND,
            CAN_MANAGE_TEAM,
            CAN_READ_AUDIT,
            CAN_MANAGE_INTEGRATIONS,
            CAN_MANAGE_KNOWLEDGE,
            CAN_CREATE_DRAFT,
        }
    ),
    "marketer": frozenset(
        {
            CAN_READ_DASHBOARD,
            CAN_IMPORT_CONTACTS,
            CAN_CREATE_CAMPAIGN,
            CAN_RUN_CAMPAIGN,
            CAN_REVIEW_DRAFT,
            CAN_SCHEDULE_SEND,
            CAN_MANAGE_KNOWLEDGE,
            CAN_CREATE_DRAFT,
        }
    ),
    "reviewer": frozenset({CAN_REVIEW_DRAFT, CAN_APPROVE_DRAFT}),
    "viewer": frozenset({CAN_READ_DASHBOARD}),
    "billing_admin": frozenset({CAN_MANAGE_BILLING}),
    "support": frozenset({CAN_USE_SUPPORT_ACCESS}),
}


class AuthorizationError(AppError):
    def __init__(self, *, code: str = "FORBIDDEN", message: str = "Access denied.") -> None:
        super().__init__(code, message, status_code=403)


class RBACService:
    """Central role-permission gate. Deny by default."""

    def has_permission(self, role: str, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, frozenset())

    def require(self, principal: CurrentPrincipal, permission: Permission) -> None:
        if not self.has_permission(principal.role, permission):
            raise AuthorizationError()


@dataclass(frozen=True)
class TenantOwnedObject:
    id: uuid.UUID
    tenant_id: uuid.UUID


class ObjectAuthorizationService:
    """Central object tenant-ownership gate; cross-tenant access fails closed."""

    def require_tenant_owner(
        self,
        *,
        principal: CurrentPrincipal,
        obj: TenantOwnedObject | None,
        action: Permission | None = None,
        rbac: RBACService | None = None,
    ) -> None:
        if obj is None or obj.tenant_id != principal.tenant_id:
            raise AuthorizationError(code="OBJECT_ACCESS_DENIED", message="Object not found.")
        if action is not None and rbac is not None:
            rbac.require(principal, action)


@dataclass(frozen=True)
class SupportAccessGrant:
    id: uuid.UUID
    tenant_id: uuid.UUID
    support_user_id: uuid.UUID
    granted_by_user_id: uuid.UUID
    reason: str
    scope: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now


class SupportAccessStore(Protocol):
    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        support_user_id: uuid.UUID,
        granted_by_user_id: uuid.UUID,
        reason: str,
        scope: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> SupportAccessGrant:
        """Create a time-boxed grant."""

    async def get_active(
        self,
        *,
        tenant_id: uuid.UUID,
        support_user_id: uuid.UUID,
        scope: str,
        now: datetime,
    ) -> SupportAccessGrant | None:
        """Return an active grant matching tenant/user/scope."""

    async def revoke(
        self,
        *,
        grant_id: uuid.UUID,
        revoked_at: datetime,
    ) -> SupportAccessGrant | None:
        """Revoke a grant."""


AuditRecorder = Callable[..., Awaitable[None]]


class SupportAccessService:
    """Time-boxed support access; no implicit or permanent support access."""

    def __init__(
        self,
        *,
        store: SupportAccessStore,
        rbac: RBACService,
        audit_record: AuditRecorder | None = None,
        default_ttl: timedelta = timedelta(minutes=60),
    ) -> None:
        self._store = store
        self._rbac = rbac
        self._audit_record = audit_record
        self._default_ttl = default_ttl

    async def grant(
        self,
        *,
        principal: CurrentPrincipal,
        support_user_id: uuid.UUID,
        reason: str,
        scope: str,
        now: datetime,
        ttl: timedelta | None = None,
    ) -> SupportAccessGrant:
        self._rbac.require(principal, CAN_GRANT_SUPPORT_ACCESS)
        duration = self._default_ttl if ttl is None else ttl
        if duration <= timedelta(0):
            raise AppError("INVALID_SUPPORT_GRANT", "Support grant must expire.", status_code=400)
        grant = await self._store.create(
            tenant_id=principal.tenant_id,
            support_user_id=support_user_id,
            granted_by_user_id=principal.user_id,
            reason=reason,
            scope=scope,
            expires_at=now + duration,
            created_at=now,
        )
        if self._audit_record is not None:
            await self._audit_record(
                event_type="support_access.granted",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="support_access_grant",
                object_id=grant.id,
                details={"scope": scope, "expires_at": grant.expires_at.isoformat()},
            )
        return grant

    async def require_active(
        self,
        *,
        principal: CurrentPrincipal,
        scope: str,
        now: datetime,
    ) -> SupportAccessGrant:
        grant = await self._store.get_active(
            tenant_id=principal.tenant_id,
            support_user_id=principal.user_id,
            scope=scope,
            now=now,
        )
        if grant is None:
            raise AuthorizationError(code="SUPPORT_ACCESS_DENIED", message="Support access denied.")
        if self._audit_record is not None:
            await self._audit_record(
                event_type="support_access.used",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="support_access_grant",
                object_id=grant.id,
                details={"scope": scope},
            )
        return grant

    async def revoke(
        self,
        *,
        principal: CurrentPrincipal,
        grant_id: uuid.UUID,
        now: datetime,
    ) -> SupportAccessGrant:
        self._rbac.require(principal, CAN_GRANT_SUPPORT_ACCESS)
        grant = await self._store.revoke(grant_id=grant_id, revoked_at=now)
        if grant is None or grant.tenant_id != principal.tenant_id:
            raise AuthorizationError(code="SUPPORT_ACCESS_DENIED", message="Support access denied.")
        if self._audit_record is not None:
            await self._audit_record(
                event_type="support_access.revoked",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="support_access_grant",
                object_id=grant.id,
                details={"scope": grant.scope},
            )
        return grant
