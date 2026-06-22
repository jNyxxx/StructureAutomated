"""Mock MVP billing access gates.

All billing decisions route through this central service. This slice deliberately
implements no real Stripe checkout, API calls, webhooks, provider objects,
secrets, or money movement.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.middleware.error_handler import AppError

BILLING_STATES = ("trialing", "active", "past_due", "canceled", "unpaid", "inactive")
ACTIVE_STATES = frozenset({"trialing", "active"})
LOCKED_STATES = frozenset({"unpaid", "canceled", "inactive"})

CAN_SEND = "can_send"
CAN_RUN_AGENTS = "can_run_agents"
CAN_CREATE_CAMPAIGN = "can_create_campaign"
CAN_EXPORT = "can_export"
DERIVED_GATES = (CAN_SEND, CAN_RUN_AGENTS, CAN_CREATE_CAMPAIGN, CAN_EXPORT)


class BillingAccessDenied(AppError):
    def __init__(self, *, code: str = "BILLING_ACCESS_DENIED") -> None:
        super().__init__(code, "Billing access denied.", status_code=403)


@dataclass(frozen=True)
class BillingPlan:
    id: uuid.UUID
    key: str
    name: str
    features: dict[str, bool]


@dataclass(frozen=True)
class TenantSubscriptionRecord:
    tenant_id: uuid.UUID
    plan: BillingPlan
    tenant_status: str
    grace_until: datetime | None = None


class BillingStore(Protocol):
    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        """Return the tenant -> subscription -> plan record."""

    async def set_status(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None,
    ) -> TenantSubscriptionRecord:
        """Explicit local/mock state transition."""


AuditRecorder = Callable[..., Awaitable[None]]


class BillingGateService:
    """Central MVP billing gate service. Unknown state/feature denies by default."""

    def __init__(self, store: BillingStore, audit_record: AuditRecorder | None = None) -> None:
        self._store = store
        self._audit_record = audit_record

    async def is_active(self, tenant_id: uuid.UUID, *, now: datetime) -> bool:
        subscription = await self._store.get_subscription(tenant_id)
        if subscription is None:
            return False
        state = subscription.tenant_status
        if state in ACTIVE_STATES:
            return True
        if state == "past_due":
            return subscription.grace_until is not None and subscription.grace_until > now
        return False

    async def has_feature(self, tenant_id: uuid.UUID, key: str, *, now: datetime) -> bool:
        if key not in DERIVED_GATES:
            return False
        subscription = await self._store.get_subscription(tenant_id)
        if subscription is None:
            return False
        if not await self.is_active(tenant_id, now=now):
            return False
        return bool(subscription.plan.features.get(key, False))

    async def require_active(self, tenant_id: uuid.UUID, *, now: datetime) -> None:
        if not await self.is_active(tenant_id, now=now):
            raise BillingAccessDenied()

    async def require_feature(self, tenant_id: uuid.UUID, key: str, *, now: datetime) -> None:
        if not await self.has_feature(tenant_id, key, now=now):
            raise BillingAccessDenied(code="BILLING_FEATURE_DENIED")

    async def can_send(self, tenant_id: uuid.UUID, *, now: datetime) -> bool:
        return await self.has_feature(tenant_id, CAN_SEND, now=now)

    async def can_run_agents(self, tenant_id: uuid.UUID, *, now: datetime) -> bool:
        return await self.has_feature(tenant_id, CAN_RUN_AGENTS, now=now)

    async def can_create_campaign(self, tenant_id: uuid.UUID, *, now: datetime) -> bool:
        return await self.has_feature(tenant_id, CAN_CREATE_CAMPAIGN, now=now)

    async def can_export(self, tenant_id: uuid.UUID, *, now: datetime) -> bool:
        return await self.has_feature(tenant_id, CAN_EXPORT, now=now)

    async def transition_mock_state(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        now: datetime,
        grace_until: datetime | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> TenantSubscriptionRecord:
        if tenant_status not in BILLING_STATES:
            raise AppError("INVALID_BILLING_STATE", "Invalid billing state.", status_code=400)
        record = await self._store.set_status(
            tenant_id=tenant_id,
            tenant_status=tenant_status,
            grace_until=grace_until,
        )
        if self._audit_record is not None:
            await self._audit_record(
                event_type="billing.mock_state_changed",
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                details={"tenant_status": tenant_status, "grace": grace_until is not None},
            )
        return record
