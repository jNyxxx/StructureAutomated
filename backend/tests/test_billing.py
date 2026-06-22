"""Mock billing schema/status/gates tests (Slice 16)."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.middleware.error_handler import AppError
from app.services.billing import (
    BILLING_STATES,
    CAN_CREATE_CAMPAIGN,
    CAN_EXPORT,
    CAN_RUN_AGENTS,
    CAN_SEND,
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_PLAN = BillingPlan(
    id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    key="mvp_mock",
    name="MVP Mock Plan",
    features={
        CAN_SEND: True,
        CAN_RUN_AGENTS: True,
        CAN_CREATE_CAMPAIGN: True,
        CAN_EXPORT: True,
    },
)
_LIMITED_PLAN = BillingPlan(
    id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
    key="limited_mock",
    name="Limited Mock Plan",
    features={CAN_CREATE_CAMPAIGN: True},
)
_NOW = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)


class _BillingStore:
    def __init__(self, record: TenantSubscriptionRecord | None = None) -> None:
        self.record = record
        self.transitions: list[str] = []

    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        if self.record is None or self.record.tenant_id != tenant_id:
            return None
        return self.record

    async def set_status(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None,
    ) -> TenantSubscriptionRecord:
        if self.record is None or self.record.tenant_id != tenant_id:
            raise AppError("SUBSCRIPTION_NOT_FOUND", "Subscription not found.", status_code=404)
        self.transitions.append(tenant_status)
        self.record = replace(self.record, tenant_status=tenant_status, grace_until=grace_until)
        return self.record


def _record(
    state: str,
    *,
    plan: BillingPlan = _PLAN,
    grace_until: datetime | None = None,
) -> TenantSubscriptionRecord:
    return TenantSubscriptionRecord(
        tenant_id=_TENANT,
        plan=plan,
        tenant_status=state,
        grace_until=grace_until,
    )


@pytest.mark.parametrize("state", BILLING_STATES)
def test_known_states_are_standardized(state: str) -> None:
    assert state in {"trialing", "active", "past_due", "canceled", "unpaid", "inactive"}


@pytest.mark.parametrize("state", ["trialing", "active"])
async def test_trialing_and_active_allow_normal_mvp_access(state: str) -> None:
    service = BillingGateService(_BillingStore(_record(state)))

    assert await service.is_active(_TENANT, now=_NOW) is True
    assert await service.can_send(_TENANT, now=_NOW) is True
    assert await service.can_run_agents(_TENANT, now=_NOW) is True
    assert await service.can_create_campaign(_TENANT, now=_NOW) is True
    assert await service.can_export(_TENANT, now=_NOW) is True


async def test_past_due_allows_during_grace_and_denies_after_grace() -> None:
    service = BillingGateService(
        _BillingStore(_record("past_due", grace_until=_NOW + timedelta(days=3)))
    )
    expired = BillingGateService(
        _BillingStore(_record("past_due", grace_until=_NOW - timedelta(seconds=1)))
    )

    assert await service.is_active(_TENANT, now=_NOW) is True
    assert await service.can_send(_TENANT, now=_NOW) is True
    assert await expired.is_active(_TENANT, now=_NOW) is False
    assert await expired.can_send(_TENANT, now=_NOW) is False


@pytest.mark.parametrize("state", ["unpaid", "canceled", "inactive"])
async def test_locked_states_deny_costly_outbound_actions(state: str) -> None:
    service = BillingGateService(_BillingStore(_record(state)))

    assert await service.is_active(_TENANT, now=_NOW) is False
    assert await service.can_send(_TENANT, now=_NOW) is False
    assert await service.can_run_agents(_TENANT, now=_NOW) is False
    assert await service.can_create_campaign(_TENANT, now=_NOW) is False
    assert await service.can_export(_TENANT, now=_NOW) is False

    with pytest.raises(AppError) as exc:
        await service.require_feature(_TENANT, CAN_SEND, now=_NOW)
    assert exc.value.status_code == 403
    assert exc.value.code == "BILLING_FEATURE_DENIED"


async def test_unknown_state_and_unknown_feature_deny_by_default() -> None:
    service = BillingGateService(_BillingStore(_record("mystery")))

    assert await service.is_active(_TENANT, now=_NOW) is False
    assert await service.has_feature(_TENANT, CAN_SEND, now=_NOW) is False
    assert await service.has_feature(_TENANT, "unknown_feature", now=_NOW) is False


async def test_missing_subscription_is_inactive_catch_all() -> None:
    service = BillingGateService(_BillingStore(None))

    assert await service.is_active(_TENANT, now=_NOW) is False
    with pytest.raises(AppError) as exc:
        await service.require_active(_TENANT, now=_NOW)
    assert exc.value.code == "BILLING_ACCESS_DENIED"


async def test_plan_feature_relationship_and_deny_unknown_feature() -> None:
    service = BillingGateService(_BillingStore(_record("active", plan=_LIMITED_PLAN)))

    assert await service.can_create_campaign(_TENANT, now=_NOW) is True
    assert await service.can_send(_TENANT, now=_NOW) is False
    assert await service.can_run_agents(_TENANT, now=_NOW) is False
    assert await service.can_export(_TENANT, now=_NOW) is False


async def test_mock_state_transition_is_explicit_testable_and_audited() -> None:
    audits: list[dict[str, object]] = []

    async def audit_record(**kwargs: object) -> None:
        audits.append(kwargs)

    store = _BillingStore(_record("trialing"))
    service = BillingGateService(store, audit_record=audit_record)

    updated = await service.transition_mock_state(
        tenant_id=_TENANT,
        tenant_status="past_due",
        now=_NOW,
        grace_until=_NOW + timedelta(days=7),
        actor_user_id=_ACTOR,
    )

    assert updated.tenant_status == "past_due"
    assert updated.grace_until == _NOW + timedelta(days=7)
    assert store.transitions == ["past_due"]
    assert audits[0]["event_type"] == "billing.mock_state_changed"
    assert audits[0]["tenant_id"] == _TENANT
    assert audits[0]["actor_user_id"] == _ACTOR
    assert audits[0]["details"] == {"tenant_status": "past_due", "grace": True}


async def test_invalid_mock_state_rejected() -> None:
    service = BillingGateService(_BillingStore(_record("active")))

    with pytest.raises(AppError) as exc:
        await service.transition_mock_state(tenant_id=_TENANT, tenant_status="paid", now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_BILLING_STATE"


def test_billing_migration_schema_rls_and_no_stripe() -> None:
    src = (
        Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0009_mock_billing.py"
    ).read_text(encoding="utf-8")

    assert "plans" in src
    assert "tenant_subscriptions" in src
    assert "tenant_id" in src
    assert "plan_id" in src
    assert "tenant_status" in src
    assert "trialing" in src and "active" in src and "inactive" in src
    assert "ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY" in src
    assert "ALTER TABLE tenant_subscriptions FORCE ROW LEVEL SECURITY" in src
    assert "tenant_id = current_setting('app.current_tenant_id', true)::uuid" in src
    assert "can_send" in src
    assert "can_run_agents" in src
    assert "can_create_campaign" in src
    assert "can_export" in src
    lowered = src.lower()
    assert "stripe" not in lowered
    assert "webhook" not in lowered
    assert "api_key" not in lowered
    assert "secret" not in lowered
