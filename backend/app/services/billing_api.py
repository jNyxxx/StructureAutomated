"""API orchestration for mock/local billing, access gates, and usage.

This service exposes the current local/demo billing state without introducing
Stripe, checkout, webhooks, invoices, payment methods, refunds, chargebacks, or
money movement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.usage_repo import UsageSnapshotRecord
from app.services.authz import CAN_MANAGE_BILLING, CAN_READ_DASHBOARD, RBACService
from app.services.billing import (
    BILLING_STATES,
    CAN_CREATE_CAMPAIGN,
    CAN_EXPORT,
    CAN_RUN_AGENTS,
    CAN_SEND,
    BillingGateService,
    TenantSubscriptionRecord,
)
from app.services.idempotency import IdempotencyOutcome, IdempotencyState


class BillingStore(Protocol):
    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None: ...


class UsageStore(Protocol):
    async def get_snapshot(self, *, tenant_id: uuid.UUID) -> UsageSnapshotRecord: ...


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
class AccessGateSnapshot:
    is_active: bool
    can_send: bool
    can_run_agents: bool
    can_create_campaign: bool
    can_export: bool
    mock_only: bool = True


@dataclass(frozen=True)
class BillingStateTransitionResult:
    subscription: TenantSubscriptionRecord
    idempotency_replay: bool = False
    mock_only: bool = True


class BillingAPIService:
    """Service facade for safe mock/local billing API behavior."""

    def __init__(
        self,
        *,
        billing: BillingGateService,
        billing_store: BillingStore,
        usage_store: UsageStore,
        rbac: RBACService,
        idempotency: IdempotencyGate,
        allow_mock_state_transition: bool,
    ) -> None:
        self._billing = billing
        self._billing_store = billing_store
        self._usage_store = usage_store
        self._rbac = rbac
        self._idempotency = idempotency
        self._allow_mock_state_transition = allow_mock_state_transition

    def _require_any(self, principal: CurrentPrincipal, permissions: tuple[str, ...]) -> None:
        allowed = any(
            self._rbac.has_permission(principal.role, permission) for permission in permissions
        )
        if not allowed:
            raise AppError("FORBIDDEN", "Access denied.", status_code=403)

    async def get_subscription(
        self, principal: CurrentPrincipal
    ) -> TenantSubscriptionRecord | None:
        self._require_any(principal, (CAN_MANAGE_BILLING, CAN_READ_DASHBOARD))
        return await self._billing_store.get_subscription(principal.tenant_id)

    async def get_access(self, principal: CurrentPrincipal, *, now: datetime) -> AccessGateSnapshot:
        self._require_any(principal, (CAN_MANAGE_BILLING, CAN_READ_DASHBOARD))
        return AccessGateSnapshot(
            is_active=await self._billing.is_active(principal.tenant_id, now=now),
            can_send=await self._billing.has_feature(principal.tenant_id, CAN_SEND, now=now),
            can_run_agents=await self._billing.has_feature(
                principal.tenant_id, CAN_RUN_AGENTS, now=now
            ),
            can_create_campaign=await self._billing.has_feature(
                principal.tenant_id, CAN_CREATE_CAMPAIGN, now=now
            ),
            can_export=await self._billing.has_feature(principal.tenant_id, CAN_EXPORT, now=now),
        )

    async def get_usage(self, principal: CurrentPrincipal) -> UsageSnapshotRecord:
        self._require_any(principal, (CAN_READ_DASHBOARD,))
        return await self._usage_store.get_snapshot(tenant_id=principal.tenant_id)

    async def transition_state_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        tenant_status: str,
        grace_until: datetime | None,
        idempotency_key: str,
        now: datetime,
    ) -> BillingStateTransitionResult:
        self._require_any(principal, (CAN_MANAGE_BILLING,))
        if not self._allow_mock_state_transition:
            raise AppError(
                "MOCK_BILLING_STATE_TRANSITION_DISABLED",
                "Mock billing state transitions are disabled in this environment.",
                status_code=403,
            )
        if tenant_status not in BILLING_STATES:
            raise AppError("INVALID_BILLING_STATE", "Invalid billing state.", status_code=400)

        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "action": "mock_billing_state_transition",
            "tenant_status": tenant_status,
            "grace_until": grace_until.isoformat() if grace_until else None,
            "mock_only": True,
        }
        outcome = await self._idempotency.begin(
            key=idempotency_key,
            request_payload=request_payload,
            now=now,
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
        )
        if outcome.is_replay:
            current = await self._billing_store.get_subscription(principal.tenant_id)
            if current is None:
                raise AppError(
                    "BILLING_SUBSCRIPTION_NOT_FOUND",
                    "Billing subscription not found.",
                    status_code=404,
                )
            return BillingStateTransitionResult(subscription=current, idempotency_replay=True)
        if outcome.state is IdempotencyState.IN_PROGRESS:
            raise AppError(
                "MOCK_BILLING_STATE_TRANSITION_IN_PROGRESS",
                "Mock billing state transition is already in progress.",
                status_code=409,
            )

        current = await self._billing_store.get_subscription(principal.tenant_id)
        if current is None:
            raise AppError(
                "BILLING_SUBSCRIPTION_NOT_FOUND",
                "Billing subscription not found.",
                status_code=404,
            )
        subscription = await self._billing.transition_mock_state(
            tenant_id=principal.tenant_id,
            tenant_status=tenant_status,
            grace_until=grace_until,
            now=now,
            actor_user_id=principal.user_id,
        )
        await self._idempotency.complete(
            key=idempotency_key,
            response_payload={
                "tenant_id": str(principal.tenant_id),
                "tenant_status": subscription.tenant_status,
                "mock_only": True,
            },
            status_code=200,
            tenant_id=principal.tenant_id,
        )
        return BillingStateTransitionResult(subscription=subscription)
