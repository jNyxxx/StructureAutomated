"""API orchestration for local/mock tenant settings, team read, and audit read.

This service deliberately avoids Clerk management, OAuth/provider calls, MFA
flows, support impersonation, platform-admin actions, and frontend wiring.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import CAN_MANAGE_TEAM, CAN_READ_AUDIT, CAN_READ_DASHBOARD, RBACService
from app.services.idempotency import IdempotencyOutcome, IdempotencyState

ALLOWED_TENANT_SETTING_KEYS = frozenset(
    {
        "timezone",
        "locale",
        "niche",
        "default_audience",
        "mock_mode",
    }
)
SENSITIVE_SETTING_KEYS = ("secret", "token", "password", "credential", "api_key", "oauth")


@dataclass(frozen=True)
class TenantSettingsRecord:
    id: uuid.UUID
    name: str
    status: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class MembershipReadRecord:
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    membership_version: int
    created_at: datetime


@dataclass(frozen=True)
class AuditEventReadRecord:
    id: uuid.UUID
    event_type: str
    actor_user_id: uuid.UUID | None
    object_type: str | None
    object_id: uuid.UUID | None
    request_id: str | None
    job_id: uuid.UUID | None
    redacted_details: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class AuditEventPage:
    items: tuple[AuditEventReadRecord, ...]
    next_cursor: str | None
    limit: int


@dataclass(frozen=True)
class TenantUpdateResult:
    tenant: TenantSettingsRecord
    idempotency_replay: bool = False
    mock_only: bool = True


class TenantSettingsStore(Protocol):
    async def get_current_tenant(self, *, tenant_id: uuid.UUID) -> TenantSettingsRecord | None: ...

    async def update_current_tenant(
        self,
        *,
        tenant_id: uuid.UUID,
        name: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> TenantSettingsRecord: ...


class MembershipReadStore(Protocol):
    async def list_memberships(self) -> list[MembershipReadRecord]: ...


class AuditReadStore(Protocol):
    async def list_recent_bounded(
        self, *, tenant_id: uuid.UUID, cursor: str | None, limit: int
    ) -> tuple[list[AuditEventReadRecord], str | None]: ...


class IdempotencyGate(Protocol):
    async def begin(
        self,
        *,
        key: str,
        request_payload: Any,
        now: datetime,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> IdempotencyOutcome: ...

    async def complete(
        self,
        *,
        key: str,
        response_payload: Any,
        status_code: int,
        tenant_id: uuid.UUID | None = None,
    ) -> None: ...


AuditRecorder = Callable[..., Awaitable[None]]


def safe_tenant_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    if not settings:
        return {}
    return {
        key: value
        for key, value in settings.items()
        if key in ALLOWED_TENANT_SETTING_KEYS
        and not any(token in key.lower() for token in SENSITIVE_SETTING_KEYS)
    }


def validate_tenant_settings_patch(settings: dict[str, Any]) -> dict[str, Any]:
    unsafe = [key for key in settings if key not in ALLOWED_TENANT_SETTING_KEYS]
    sensitive = [
        key for key in settings if any(token in key.lower() for token in SENSITIVE_SETTING_KEYS)
    ]
    if unsafe or sensitive:
        raise AppError(
            "UNSAFE_TENANT_SETTINGS_FIELD",
            "Tenant settings field is not allowed.",
            status_code=400,
        )
    return dict(settings)


class SettingsAPIService:
    """Thin service for tenant settings, team read, and audit read APIs."""

    def __init__(
        self,
        *,
        tenants: TenantSettingsStore,
        memberships: MembershipReadStore,
        audit_events: AuditReadStore,
        rbac: RBACService,
        idempotency: IdempotencyGate,
        audit_record: AuditRecorder,
    ) -> None:
        self._tenants = tenants
        self._memberships = memberships
        self._audit_events = audit_events
        self._rbac = rbac
        self._idempotency = idempotency
        self._audit_record = audit_record

    def _require_any(self, principal: CurrentPrincipal, permissions: tuple[str, ...]) -> None:
        allowed = any(
            self._rbac.has_permission(principal.role, permission) for permission in permissions
        )
        if not allowed:
            raise AppError("FORBIDDEN", "Access denied.", status_code=403)

    async def get_current_tenant(self, principal: CurrentPrincipal) -> TenantSettingsRecord:
        self._require_any(principal, (CAN_READ_DASHBOARD, CAN_MANAGE_TEAM))
        tenant = await self._tenants.get_current_tenant(tenant_id=principal.tenant_id)
        if tenant is None:
            raise AppError("TENANT_NOT_FOUND", "Tenant not found.", status_code=404)
        return tenant

    async def update_current_tenant_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        idempotency_key: str,
        now: datetime,
        name: str | None = None,
        settings_patch: dict[str, Any] | None = None,
    ) -> TenantUpdateResult:
        self._require_any(principal, (CAN_MANAGE_TEAM,))
        safe_patch = validate_tenant_settings_patch(settings_patch or {})
        if name is not None and not name.strip():
            raise AppError("INVALID_TENANT_NAME", "Tenant name is required.", status_code=400)

        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "action": "tenant_settings_update",
            "name": name.strip() if name is not None else None,
            "settings_patch": safe_patch,
        }
        outcome = await self._idempotency.begin(
            key=idempotency_key,
            request_payload=request_payload,
            now=now,
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
        )
        if outcome.is_replay:
            tenant = await self.get_current_tenant(principal)
            return TenantUpdateResult(tenant=tenant, idempotency_replay=True)
        if outcome.state is IdempotencyState.IN_PROGRESS:
            raise AppError(
                "TENANT_SETTINGS_UPDATE_IN_PROGRESS",
                "Tenant settings update is already in progress.",
                status_code=409,
            )

        current = await self.get_current_tenant(principal)
        merged_settings = {**safe_tenant_settings(current.settings), **safe_patch}
        tenant = await self._tenants.update_current_tenant(
            tenant_id=principal.tenant_id,
            name=name.strip() if name is not None else None,
            settings=merged_settings,
        )
        changed_fields = []
        if name is not None:
            changed_fields.append("name")
        if safe_patch:
            changed_fields.append("settings")
        await self._audit_record(
            event_type="tenant.settings_updated",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="tenant",
            object_id=principal.tenant_id,
            details={"changed_fields": changed_fields},
        )
        await self._idempotency.complete(
            key=idempotency_key,
            response_payload={
                "tenant_id": str(principal.tenant_id),
                "changed_fields": changed_fields,
                "mock_only": True,
            },
            status_code=200,
            tenant_id=principal.tenant_id,
        )
        return TenantUpdateResult(tenant=tenant)

    async def list_memberships(
        self, principal: CurrentPrincipal
    ) -> tuple[MembershipReadRecord, ...]:
        self._require_any(principal, (CAN_MANAGE_TEAM,))
        return tuple(await self._memberships.list_memberships())

    async def list_audit_events(
        self, principal: CurrentPrincipal, *, cursor: str | None, limit: int
    ) -> AuditEventPage:
        self._require_any(principal, (CAN_READ_AUDIT,))
        items, next_cursor = await self._audit_events.list_recent_bounded(
            tenant_id=principal.tenant_id,
            cursor=cursor,
            limit=limit,
        )
        return AuditEventPage(items=tuple(items), next_cursor=next_cursor, limit=limit)
