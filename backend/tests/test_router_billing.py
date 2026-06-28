"""Router and service tests for Phase 2 P2-7 mock/local billing APIs."""

import inspect
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.main import create_app
from app.middleware.error_handler import AppError
from app.repositories.usage_repo import UsageSnapshotRecord
from app.routers import billing as billing_router
from app.routers.billing import billing_api_service, stripe_billing_api_service
from app.services.authz import RBACService
from app.services.billing import BillingGateService, BillingPlan, TenantSubscriptionRecord
from app.services.billing_api import (
    AccessGateSnapshot,
    BillingAPIService,
    BillingStateTransitionResult,
)
from app.services.idempotency import IdempotencyOutcome, IdempotencyState

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_PLAN_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "billing-key-1"}
_FEATURES = {
    "can_send": True,
    "can_run_agents": True,
    "can_create_campaign": True,
    "can_export": True,
}


def _principal(role: str = "owner") -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=_USER,
        email="owner@example.com",
        tenant_id=_TENANT,
        role=role,
        membership_version=1,
        mfa_verified=True,
    )


def _subscription(
    status: str = "active", grace_until: datetime | None = None
) -> TenantSubscriptionRecord:
    return TenantSubscriptionRecord(
        tenant_id=_TENANT,
        plan=BillingPlan(
            id=_PLAN_ID,
            key="mock_growth",
            name="Mock Growth",
            features=dict(_FEATURES),
        ),
        tenant_status=status,
        grace_until=grace_until,
    )


def _usage() -> UsageSnapshotRecord:
    return UsageSnapshotRecord(
        contacts_total=10,
        contact_imports_total=2,
        campaigns_total=3,
        drafts_total=4,
        outbound_mock_sent=5,
        outbound_blocked=1,
        send_gate_denied=2,
        followups_mock_sent=1,
        followups_skipped=1,
        research_runs_total=6,
        outcome_events_total=7,
    )


class _FakeStripeBillingAPIService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def create_checkout_session(self, principal: CurrentPrincipal, **kwargs: Any) -> object:
        self.calls.append({"method": "create_checkout_session", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        raise AssertionError("Stripe checkout skeleton must fail closed in P3-6e")

    async def create_billing_portal_session(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> object:
        self.calls.append(
            {"method": "create_billing_portal_session", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        raise AssertionError("Stripe portal skeleton must fail closed in P3-6e")


class _FakeBillingAPIService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def get_subscription(
        self, principal: CurrentPrincipal
    ) -> TenantSubscriptionRecord | None:
        self.calls.append({"method": "get_subscription", "principal": principal})
        if self.error is not None:
            raise self.error
        return _subscription()

    async def get_access(self, principal: CurrentPrincipal, **kwargs: Any) -> AccessGateSnapshot:
        self.calls.append({"method": "get_access", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        return AccessGateSnapshot(
            is_active=True,
            can_send=True,
            can_run_agents=True,
            can_create_campaign=True,
            can_export=True,
        )

    async def get_usage(self, principal: CurrentPrincipal) -> UsageSnapshotRecord:
        self.calls.append({"method": "get_usage", "principal": principal})
        if self.error is not None:
            raise self.error
        return _usage()

    async def transition_state_idempotent(
        self,
        principal: CurrentPrincipal,
        **kwargs: Any,
    ) -> BillingStateTransitionResult:
        self.calls.append(
            {"method": "transition_state_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        status = kwargs["tenant_status"]
        if status not in {"trialing", "active", "past_due", "canceled", "unpaid", "inactive"}:
            raise AppError("INVALID_BILLING_STATE", "Invalid billing state.", status_code=400)
        return BillingStateTransitionResult(
            subscription=_subscription(status=status, grace_until=kwargs.get("grace_until")),
            idempotency_replay=self.replay,
        )


def _client(
    service: _FakeBillingAPIService | None = None,
    stripe_service: _FakeStripeBillingAPIService | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        app.dependency_overrides[billing_api_service] = lambda: service
    if stripe_service is not None:
        app.dependency_overrides[stripe_billing_api_service] = lambda: stripe_service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("get", "/api/v1/billing/subscription", None, None),
        ("get", "/api/v1/billing/access", None, None),
        ("get", "/api/v1/usage", None, None),
        ("post", "/api/v1/billing/state-transition", {"tenant_status": "active"}, _HEADERS),
        ("post", "/api/v1/billing/checkout-session", {}, None),
        ("post", "/api/v1/billing/portal-session", {}, None),
    ],
)
def test_billing_routes_require_authentication(
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    headers: dict[str, str] | None,
) -> None:
    resp = TestClient(create_app(), raise_server_exceptions=False).request(
        method, path, json=json_body, headers=headers
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_billing_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/billing/subscription" in spec
    assert "/api/v1/billing/access" in spec
    assert "/api/v1/usage" in spec
    assert "/api/v1/billing/state-transition" in spec
    assert "/api/v1/billing/checkout-session" in spec
    assert "/api/v1/billing/portal-session" in spec


def test_checkout_session_endpoint_fails_closed_when_disabled() -> None:
    fake = _FakeStripeBillingAPIService(
        error=AppError(
            "STRIPE_CHECKOUT_NOT_AVAILABLE",
            "Stripe checkout is not available.",
            status_code=503,
        )
    )

    resp = _client(stripe_service=fake).post("/api/v1/billing/checkout-session", json={})

    assert resp.status_code == 503
    error = resp.json()["error"]
    assert error["code"] == "STRIPE_CHECKOUT_NOT_AVAILABLE"
    assert error["message"] == "Stripe checkout is not available."
    assert error["details"] == {}
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_portal_session_endpoint_fails_closed_when_disabled() -> None:
    fake = _FakeStripeBillingAPIService(
        error=AppError(
            "STRIPE_PORTAL_NOT_AVAILABLE",
            "Stripe billing portal is not available.",
            status_code=503,
        )
    )

    resp = _client(stripe_service=fake).post("/api/v1/billing/portal-session", json={})

    assert resp.status_code == 503
    error = resp.json()["error"]
    assert error["code"] == "STRIPE_PORTAL_NOT_AVAILABLE"
    assert error["message"] == "Stripe billing portal is not available."
    assert error["details"] == {}
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_checkout_and_portal_routes_reject_client_supplied_tenant_id() -> None:
    fake = _FakeStripeBillingAPIService()

    checkout = _client(stripe_service=fake).post(
        "/api/v1/billing/checkout-session",
        json={"tenant_id": "99999999-9999-9999-9999-999999999999"},
    )
    portal = _client(stripe_service=fake).post(
        "/api/v1/billing/portal-session",
        json={"tenant_id": "99999999-9999-9999-9999-999999999999"},
    )

    assert checkout.status_code == 422
    assert portal.status_code == 422
    assert fake.calls == []


def test_get_subscription_returns_safe_mock_subscription_dto() -> None:
    fake = _FakeBillingAPIService()
    resp = _client(fake).get("/api/v1/billing/subscription")
    assert resp.status_code == 200
    body = resp.json()
    assert body["subscription"]["tenant_status"] == "active"
    assert body["subscription"]["plan"]["key"] == "mock_growth"
    assert body["subscription"]["plan"]["features"] == _FEATURES
    assert body["mock_only"] is True
    assert "tenant_id" not in body["subscription"]
    assert "provider_customer" not in str(body).lower()
    assert "payment" not in str(body).lower()
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_get_access_returns_all_derived_gates() -> None:
    fake = _FakeBillingAPIService()
    resp = _client(fake).get("/api/v1/billing/access")
    assert resp.status_code == 200
    assert resp.json()["access"] == {
        "is_active": True,
        "can_send": True,
        "can_run_agents": True,
        "can_create_campaign": True,
        "can_export": True,
        "mock_only": True,
    }


def test_get_usage_returns_count_only_mock_metrics_without_sensitive_data() -> None:
    fake = _FakeBillingAPIService()
    resp = _client(fake).get("/api/v1/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["usage"] == {
        "contacts_total": 10,
        "contact_imports_total": 2,
        "campaigns_total": 3,
        "drafts_total": 4,
        "outbound_mock_sent": 5,
        "outbound_blocked": 1,
        "send_gate_denied": 2,
        "followups_mock_sent": 1,
        "followups_skipped": 1,
        "research_runs_total": 6,
        "outcome_events_total": 7,
        "mock_only": True,
    }
    assert body["mock_only"] is True
    forbidden = ("email", "phone", "secret", "token", "provider", "payment")
    assert all(term not in str(body).lower() for term in forbidden)


def test_state_transition_requires_idempotency_key() -> None:
    fake = _FakeBillingAPIService()
    resp = _client(fake).post("/api/v1/billing/state-transition", json={"tenant_status": "active"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_state_transition_rejects_invalid_state() -> None:
    fake = _FakeBillingAPIService()
    resp = _client(fake).post(
        "/api/v1/billing/state-transition",
        json={"tenant_status": "paid"},
        headers=_HEADERS,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_BILLING_STATE"


def test_state_transition_is_idempotency_replay_safe() -> None:
    fake = _FakeBillingAPIService(replay=True)
    first = _client(fake).post(
        "/api/v1/billing/state-transition",
        json={"tenant_status": "past_due", "grace_until": "2026-06-28T12:00:00Z"},
        headers=_HEADERS,
    )
    second = _client(fake).post(
        "/api/v1/billing/state-transition",
        json={"tenant_status": "past_due", "grace_until": "2026-06-28T12:00:00Z"},
        headers=_HEADERS,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["idempotency_replay"] is True


class _BillingStore:
    def __init__(self, record: TenantSubscriptionRecord | None) -> None:
        self.record = record
        self.transitions: list[str] = []

    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        assert tenant_id == _TENANT
        return self.record

    async def set_status(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None,
    ) -> TenantSubscriptionRecord:
        assert tenant_id == _TENANT
        self.transitions.append(tenant_status)
        assert self.record is not None
        self.record = TenantSubscriptionRecord(
            tenant_id=self.record.tenant_id,
            plan=self.record.plan,
            tenant_status=tenant_status,
            grace_until=grace_until,
        )
        return self.record


class _UsageStore:
    async def get_snapshot(self, *, tenant_id: uuid.UUID) -> UsageSnapshotRecord:
        assert tenant_id == _TENANT
        return _usage()


class _Idempotency:
    def __init__(self, state: IdempotencyState = IdempotencyState.NEW) -> None:
        self.state = state
        self.completed: list[dict[str, Any]] = []

    async def begin(self, **kwargs: Any) -> IdempotencyOutcome:
        assert kwargs["tenant_id"] == _TENANT
        assert kwargs["actor_user_id"] == _USER
        return IdempotencyOutcome(self.state)

    async def complete(self, **kwargs: Any) -> None:
        self.completed.append(kwargs)


async def _service(
    *,
    record: TenantSubscriptionRecord | None = None,
    allow_mock_state_transition: bool = True,
    idempotency: _Idempotency | None = None,
) -> tuple[BillingAPIService, _BillingStore, _Idempotency, list[dict[str, Any]]]:
    store = _BillingStore(record if record is not None else _subscription())
    idem = idempotency or _Idempotency()
    audits: list[dict[str, Any]] = []

    async def audit_record(**kwargs: Any) -> None:
        audits.append(kwargs)

    service = BillingAPIService(
        billing=BillingGateService(store, audit_record),
        billing_store=store,
        usage_store=_UsageStore(),
        rbac=RBACService(),
        idempotency=idem,
        allow_mock_state_transition=allow_mock_state_transition,
    )
    return service, store, idem, audits


@pytest.mark.asyncio
async def test_service_access_reflects_past_due_grace() -> None:
    service, _, _, _ = await _service(
        record=_subscription("past_due", grace_until=_NOW + timedelta(days=3))
    )
    access = await service.get_access(_principal(), now=_NOW)
    assert access.is_active is True
    assert access.can_send is True
    expired_service, _, _, _ = await _service(
        record=_subscription("past_due", grace_until=_NOW - timedelta(seconds=1))
    )
    expired = await expired_service.get_access(_principal(), now=_NOW)
    assert expired.is_active is False
    assert expired.can_send is False


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["inactive", "unpaid", "canceled"])
async def test_service_locked_states_block_costly_access(state: str) -> None:
    service, _, _, _ = await _service(record=_subscription(state))
    access = await service.get_access(_principal(), now=_NOW)
    assert access.is_active is False
    assert access.can_send is False
    assert access.can_run_agents is False
    assert access.can_create_campaign is False
    assert access.can_export is False


@pytest.mark.asyncio
async def test_service_access_returns_active_local_mvp_mock_features() -> None:
    record = TenantSubscriptionRecord(
        tenant_id=_TENANT,
        tenant_status="active",
        grace_until=None,
        plan=BillingPlan(
            id=_PLAN_ID,
            key="mvp_mock",
            name="MVP Mock Plan",
            features=dict(_FEATURES),
        ),
    )
    service, _, _, _ = await _service(record=record)

    access = await service.get_access(_principal(), now=_NOW)

    assert access.is_active is True
    assert access.can_send is True
    assert access.can_run_agents is True
    assert access.can_create_campaign is True
    assert access.can_export is True
    assert access.mock_only is True


@pytest.mark.asyncio
async def test_service_state_transition_requires_billing_permission() -> None:
    service, _, _, _ = await _service()
    with pytest.raises(AppError) as exc:
        await service.transition_state_idempotent(
            _principal("marketer"),
            tenant_status="active",
            grace_until=None,
            idempotency_key="k",
            now=_NOW,
        )
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_service_state_transition_rejects_production_guard() -> None:
    service, _, _, _ = await _service(allow_mock_state_transition=False)
    with pytest.raises(AppError) as exc:
        await service.transition_state_idempotent(
            _principal("owner"),
            tenant_status="active",
            grace_until=None,
            idempotency_key="k",
            now=_NOW,
        )
    assert exc.value.code == "MOCK_BILLING_STATE_TRANSITION_DISABLED"


@pytest.mark.asyncio
async def test_service_state_transition_audits_mock_change() -> None:
    service, store, idem, audits = await _service()
    result = await service.transition_state_idempotent(
        _principal("owner"),
        tenant_status="past_due",
        grace_until=_NOW + timedelta(days=7),
        idempotency_key="k",
        now=_NOW,
    )
    assert result.subscription.tenant_status == "past_due"
    assert store.transitions == ["past_due"]
    assert idem.completed
    assert audits[0]["event_type"] == "billing.mock_state_changed"
    assert audits[0]["details"] == {"tenant_status": "past_due", "grace": True}


async def test_billing_di_opens_tenant_session_with_principal_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: dict[str, Any] = {}

    class _FakeConn:
        pass

    @asynccontextmanager
    async def fake_tenant_session(
        *, tenant_id: Any, actor_id: Any = None, request_id: Any = None
    ) -> Any:
        opened["tenant_id"] = tenant_id
        opened["actor_id"] = actor_id
        yield _FakeConn()

    monkeypatch.setattr(billing_router, "tenant_session", fake_tenant_session)
    gen = billing_router.billing_api_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, billing_router.BillingAPIService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


def test_billing_router_does_not_import_payment_or_provider_clients() -> None:
    source = inspect.getsource(billing_router).lower()
    forbidden = (
        "\nimport " + "stripe",
        "\nfrom " + "stripe",
        "api." + "stripe",
        "checkout.sessions" + ".create",
        "billing_portal.sessions" + ".create",
        "boto3",
        "sendgrid",
        "mailgun",
        "twilio",
        "provider_customer",
        "provider_subscription",
        "payment_method",
    )
    assert all(term not in source for term in forbidden)
