"""API orchestration for mock/local compliance and suppression routes.

This service keeps routers thin while adding RBAC, idempotency, pagination, and
safe MVP constraints around the lower-level ComplianceGateService. It does not
perform provider calls, sending, webhooks, live scraping, privacy export, or
privacy deletion.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import (
    CAN_MANAGE_INTEGRATIONS,
    CAN_READ_DASHBOARD,
    CAN_RUN_CAMPAIGN,
    RBACService,
)
from app.services.compliance import (
    DEFAULT_JURISDICTION,
    ComplianceGateService,
    ComplianceProfileRecord,
    SuppressionRecord,
    hash_contact_identifier,
)
from app.services.idempotency import IdempotencyOutcome, IdempotencyState


class ComplianceReadWriteStore(Protocol):
    async def get_active_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
    ) -> SuppressionRecord | None: ...

    async def get_suppression(
        self, *, tenant_id: uuid.UUID, suppression_id: uuid.UUID
    ) -> SuppressionRecord | None: ...

    async def list_suppressions(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[SuppressionRecord], str | None]: ...


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


@dataclass(frozen=True)
class SuppressionPage:
    items: tuple[SuppressionRecord, ...]
    next_cursor: str | None
    limit: int


@dataclass(frozen=True)
class ComplianceProfileActionResult:
    profile: ComplianceProfileRecord
    idempotency_replay: bool = False
    mock_only: bool = True


@dataclass(frozen=True)
class SuppressionActionResult:
    suppression: SuppressionRecord
    idempotency_replay: bool = False
    mock_only: bool = True


class ComplianceAPIService:
    """Service facade for compliance profile + suppression API behavior."""

    def __init__(
        self,
        *,
        compliance: ComplianceGateService,
        store: ComplianceReadWriteStore,
        rbac: RBACService,
        idempotency: IdempotencyGate,
    ) -> None:
        self._compliance = compliance
        self._store = store
        self._rbac = rbac
        self._idempotency = idempotency

    def _require_any(self, principal: CurrentPrincipal, permissions: tuple[str, ...]) -> None:
        allowed = any(
            self._rbac.has_permission(principal.role, permission) for permission in permissions
        )
        if not allowed:
            raise AppError("FORBIDDEN", "Access denied.", status_code=403)

    async def get_profile(self, principal: CurrentPrincipal) -> ComplianceProfileRecord:
        self._require_any(principal, (CAN_READ_DASHBOARD, CAN_MANAGE_INTEGRATIONS))
        return await self._compliance.profile(principal.tenant_id)

    async def update_profile_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        idempotency_key: str,
        now: datetime,
        jurisdiction: str = DEFAULT_JURISDICTION,
        sending_review_required: bool = True,
        live_sending_allowed: bool = False,
        sms_allowed: bool = False,
    ) -> ComplianceProfileActionResult:
        self._require_any(principal, (CAN_MANAGE_INTEGRATIONS,))
        if live_sending_allowed:
            raise AppError(
                "LIVE_SENDING_DEFERRED",
                "Live sending remains deferred during the local/mock MVP.",
                status_code=400,
            )
        if sms_allowed:
            raise AppError(
                "SMS_COMPLIANCE_DEFERRED",
                "SMS remains deferred during the local/mock MVP.",
                status_code=400,
            )

        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "action": "compliance_profile_update",
            "jurisdiction": jurisdiction,
            "sending_review_required": sending_review_required,
            "live_sending_allowed": live_sending_allowed,
            "sms_allowed": sms_allowed,
        }
        outcome = await self._idempotency.begin(
            key=idempotency_key,
            request_payload=request_payload,
            now=now,
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
        )
        if outcome.is_replay:
            return ComplianceProfileActionResult(
                profile=await self._compliance.profile(principal.tenant_id),
                idempotency_replay=True,
            )
        if outcome.state is IdempotencyState.IN_PROGRESS:
            raise AppError(
                "COMPLIANCE_PROFILE_UPDATE_IN_PROGRESS",
                "Compliance profile update is already in progress.",
                status_code=409,
            )

        profile = await self._compliance.upsert_profile(
            tenant_id=principal.tenant_id,
            jurisdiction=jurisdiction,
            sending_review_required=sending_review_required,
            live_sending_allowed=live_sending_allowed,
            sms_allowed=sms_allowed,
            actor_user_id=principal.user_id,
        )
        await self._idempotency.complete(
            key=idempotency_key,
            response_payload={"tenant_id": str(principal.tenant_id), "mock_only": True},
            status_code=200,
            tenant_id=principal.tenant_id,
        )
        return ComplianceProfileActionResult(profile=profile)

    async def list_suppressions(
        self,
        principal: CurrentPrincipal,
        *,
        cursor: str | None,
        limit: int,
    ) -> SuppressionPage:
        self._require_any(principal, (CAN_READ_DASHBOARD, CAN_MANAGE_INTEGRATIONS))
        rows, next_cursor = await self._store.list_suppressions(
            tenant_id=principal.tenant_id,
            cursor=cursor,
            limit=limit,
        )
        return SuppressionPage(items=tuple(rows), next_cursor=next_cursor, limit=limit)

    async def add_suppression_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        idempotency_key: str,
        now: datetime,
        channel: str,
        contact_identifier: str,
        reason: str,
        source: str,
        never_contact: bool = True,
    ) -> SuppressionActionResult:
        self._require_any(principal, (CAN_MANAGE_INTEGRATIONS, CAN_RUN_CAMPAIGN))
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "action": "suppression_add",
            "channel": channel,
            "contact_identifier": contact_identifier,
            "reason": reason,
            "source": source,
            "never_contact": never_contact,
        }
        outcome = await self._idempotency.begin(
            key=idempotency_key,
            request_payload=request_payload,
            now=now,
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
        )
        contact_hash = hash_contact_identifier(
            channel=channel,
            contact_identifier=contact_identifier,
        )
        if outcome.is_replay:
            existing = await self._store.get_active_suppression(
                tenant_id=principal.tenant_id,
                channel=channel,
                contact_hash=contact_hash,
            )
            if existing is None:
                raise AppError("SUPPRESSION_NOT_FOUND", "Suppression not found.", status_code=404)
            return SuppressionActionResult(suppression=existing, idempotency_replay=True)
        if outcome.state is IdempotencyState.IN_PROGRESS:
            raise AppError(
                "SUPPRESSION_ADD_IN_PROGRESS",
                "Suppression add is already in progress.",
                status_code=409,
            )

        existing = await self._store.get_active_suppression(
            tenant_id=principal.tenant_id,
            channel=channel,
            contact_hash=contact_hash,
        )
        if existing is not None:
            suppression = existing
        else:
            suppression = await self._compliance.add_suppression(
                tenant_id=principal.tenant_id,
                channel=channel,
                contact_identifier=contact_identifier,
                reason=reason,
                source=source,
                now=now,
                actor_user_id=principal.user_id,
                never_contact=never_contact,
            )
        await self._idempotency.complete(
            key=idempotency_key,
            response_payload={
                "suppression_id": str(suppression.id),
                "tenant_id": str(principal.tenant_id),
                "mock_only": True,
            },
            status_code=201,
            tenant_id=principal.tenant_id,
        )
        return SuppressionActionResult(suppression=suppression)

    async def reinstate_suppression_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        suppression_id: uuid.UUID,
        idempotency_key: str,
        now: datetime,
    ) -> SuppressionActionResult:
        self._require_any(principal, (CAN_MANAGE_INTEGRATIONS,))
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "action": "suppression_reinstate",
            "suppression_id": str(suppression_id),
        }
        outcome = await self._idempotency.begin(
            key=idempotency_key,
            request_payload=request_payload,
            now=now,
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
        )
        if outcome.is_replay:
            existing = await self._store.get_suppression(
                tenant_id=principal.tenant_id,
                suppression_id=suppression_id,
            )
            if existing is None:
                raise AppError("SUPPRESSION_NOT_FOUND", "Suppression not found.", status_code=404)
            return SuppressionActionResult(suppression=existing, idempotency_replay=True)
        if outcome.state is IdempotencyState.IN_PROGRESS:
            raise AppError(
                "SUPPRESSION_REINSTATE_IN_PROGRESS",
                "Suppression reinstate is already in progress.",
                status_code=409,
            )

        suppression = await self._compliance.revoke_suppression(
            tenant_id=principal.tenant_id,
            suppression_id=suppression_id,
            now=now,
            actor_user_id=principal.user_id,
        )
        await self._idempotency.complete(
            key=idempotency_key,
            response_payload={
                "suppression_id": str(suppression.id),
                "tenant_id": str(principal.tenant_id),
                "mock_only": True,
            },
            status_code=200,
            tenant_id=principal.tenant_id,
        )
        return SuppressionActionResult(suppression=suppression)
