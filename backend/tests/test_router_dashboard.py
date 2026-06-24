"""Router tests for Phase 2 P2-5 mock/local dashboard APIs."""

import inspect
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.main import create_app
from app.middleware.error_handler import AppError
from app.repositories.outcomes_repo import OutcomeEventRecord
from app.routers import deliverability as deliverability_router
from app.routers import outcomes as outcomes_router
from app.routers.deliverability import dashboard_service as deliverability_dashboard_service
from app.routers.outcomes import dashboard_service as outcomes_dashboard_service
from app.services.dashboard import (
    DeliverabilityDashboardResult,
    MailboxDashboardResult,
    MockOutcomeEventResult,
    OutcomesDashboardResult,
    ROIDashboardResult,
)
from app.services.deliverability import (
    CampaignDeliverabilitySummary,
    DeliverabilitySummary,
    MailboxHealthSummary,
)
from app.services.outcomes import CampaignOutcomesSummary, OutcomesSummary, ROISummary

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_EVENT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_OUTBOUND = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "outcome-key-1"}
_EVENT_BODY = {
    "campaign_id": str(_CAMPAIGN),
    "contact_id": str(_CONTACT),
    "event_type": "reply_received",
    "outbound_message_id": str(_OUTBOUND),
    "note": "mock reply",
    "occurred_at": _NOW.isoformat(),
}


def _principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=_USER,
        email="owner@example.com",
        tenant_id=_TENANT,
        role="owner",
        membership_version=1,
        mfa_verified=True,
    )


def _deliverability_summary(
    campaign: bool = False,
) -> DeliverabilitySummary | CampaignDeliverabilitySummary:
    if campaign:
        return CampaignDeliverabilitySummary(
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            sent=10,
            blocked=1,
            duplicate_denied=2,
            suppressed=3,
            safety_denied=4,
            throttled=5,
            followup_sent=6,
            followup_skipped=7,
            mock_bounced=0,
            mock_complained=0,
            mock_opened=3,
            mock_replied=0,
            date_from=None,
            date_to=None,
        )
    return DeliverabilitySummary(
        tenant_id=_TENANT,
        sent=10,
        blocked=1,
        duplicate_denied=2,
        suppressed=3,
        safety_denied=4,
        throttled=5,
        followup_sent=6,
        followup_skipped=7,
        mock_bounced=0,
        mock_complained=0,
        mock_opened=3,
        mock_replied=0,
        date_from=None,
        date_to=None,
    )


def _outcomes_summary(campaign: bool = False) -> OutcomesSummary | CampaignOutcomesSummary:
    if campaign:
        return CampaignOutcomesSummary(
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            reply_count=10,
            positive_reply_count=4,
            meeting_booked_count=2,
            opportunity_count=1,
            deal_won_count=1,
            deal_lost_count=0,
            unsubscribe_count=0,
            bounce_count=1,
            complaint_count=0,
            reply_rate=0.5,
            positive_reply_rate=0.2,
            meeting_rate=0.1,
            opportunity_rate=0.05,
            win_rate=1.0,
            date_from=None,
            date_to=None,
        )
    return OutcomesSummary(
        tenant_id=_TENANT,
        reply_count=10,
        positive_reply_count=4,
        meeting_booked_count=2,
        opportunity_count=1,
        deal_won_count=1,
        deal_lost_count=0,
        unsubscribe_count=0,
        bounce_count=1,
        complaint_count=0,
        reply_rate=0.5,
        positive_reply_rate=0.2,
        meeting_rate=0.1,
        opportunity_rate=0.05,
        win_rate=1.0,
        date_from=None,
        date_to=None,
    )


def _event() -> OutcomeEventRecord:
    return OutcomeEventRecord(
        id=_EVENT,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        outbound_message_id=_OUTBOUND,
        event_type="reply_received",
        note="mock reply",
        idempotency_key="namespaced-secret-key",
        occurred_at=_NOW,
        created_at=_NOW,
    )


class _FakeDashboardService:
    def __init__(self, *, error: Exception | None = None, campaign: bool = False) -> None:
        self.error = error
        self.campaign = campaign
        self.calls: list[dict[str, Any]] = []

    async def get_deliverability_summary(self, principal: CurrentPrincipal, **kwargs: Any) -> Any:
        self.calls.append(
            {"method": "get_deliverability_summary", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        return DeliverabilityDashboardResult(summary=_deliverability_summary(self.campaign))

    def get_mailbox_health(self, principal: CurrentPrincipal) -> MailboxDashboardResult:
        self.calls.append({"method": "get_mailbox_health", "principal": principal})
        if self.error is not None:
            raise self.error
        return MailboxDashboardResult(
            health=MailboxHealthSummary(
                tenant_id=_TENANT,
                mock_domain="mock-11111111.example.com",
                dkim_valid=True,
                spf_valid=True,
                dmarc_valid=True,
                reputation_score=88,
            )
        )

    async def get_outcomes_summary(self, principal: CurrentPrincipal, **kwargs: Any) -> Any:
        self.calls.append({"method": "get_outcomes_summary", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        return OutcomesDashboardResult(summary=_outcomes_summary(self.campaign))

    async def get_roi_summary(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> ROIDashboardResult:
        self.calls.append({"method": "get_roi_summary", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        return ROIDashboardResult(
            summary=ROISummary(
                tenant_id=_TENANT,
                campaign_id=_CAMPAIGN,
                sent_count=10,
                estimated_cost_cents=100,
                estimated_pipeline_value_cents=5000,
                estimated_won_value_cents=10000,
                estimated_roi_percent=9900.0,
            )
        )

    async def record_mock_outcome_event(self, principal: CurrentPrincipal, **kwargs: Any) -> Any:
        self.calls.append({"method": "record_mock_outcome_event", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        return MockOutcomeEventResult(event=_event())


def _client(
    service: _FakeDashboardService | None = None,
    *,
    override_deliverability: bool = True,
    override_outcomes: bool = True,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        if override_deliverability:
            app.dependency_overrides[deliverability_dashboard_service] = lambda: service
        if override_outcomes:
            app.dependency_overrides[outcomes_dashboard_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("get", "/api/v1/deliverability", None, None),
        ("get", "/api/v1/deliverability/mailboxes", None, None),
        ("get", "/api/v1/outcomes", None, None),
        ("get", f"/api/v1/outcomes/roi?campaign_id={_CAMPAIGN}", None, None),
        ("post", "/api/v1/outcomes/mock-events", _EVENT_BODY, _HEADERS),
    ],
)
def test_dashboard_routes_require_authentication(
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


def test_dashboard_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/deliverability" in spec
    assert "get" in spec["/api/v1/deliverability"]
    assert "/api/v1/deliverability/mailboxes" in spec
    assert "get" in spec["/api/v1/deliverability/mailboxes"]
    assert "/api/v1/outcomes" in spec
    assert "get" in spec["/api/v1/outcomes"]
    assert "/api/v1/outcomes/roi" in spec
    assert "get" in spec["/api/v1/outcomes/roi"]
    assert "/api/v1/outcomes/mock-events" in spec
    assert "post" in spec["/api/v1/outcomes/mock-events"]


def test_mock_outcome_events_requires_idempotency_key() -> None:
    fake = _FakeDashboardService()
    resp = _client(fake).post("/api/v1/outcomes/mock-events", json=_EVENT_BODY)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_deliverability_tenant_summary_returns_safe_dto() -> None:
    fake = _FakeDashboardService()
    resp = _client(fake).get("/api/v1/deliverability")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["deliverability", "mock_only"]
    assert body["deliverability"]["sent"] == 10
    assert body["deliverability"]["campaign_id"] is None
    assert body["deliverability"]["mock_only"] is True
    assert body["mock_only"] is True
    assert "tenant_id" not in body["deliverability"]
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_deliverability_campaign_summary_uses_object_auth_context() -> None:
    fake = _FakeDashboardService(campaign=True)
    resp = _client(fake).get(f"/api/v1/deliverability?campaign_id={_CAMPAIGN}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deliverability"]["campaign_id"] == str(_CAMPAIGN)
    assert fake.calls[0]["campaign_id"] == _CAMPAIGN


def test_deliverability_campaign_cross_tenant_fails_closed() -> None:
    fake = _FakeDashboardService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(fake).get(f"/api/v1/deliverability?campaign_id={_CAMPAIGN}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


def test_mailbox_route_returns_mock_health_without_secrets() -> None:
    fake = _FakeDashboardService()
    resp = _client(fake).get("/api/v1/deliverability/mailboxes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mailbox_health"]["mock_domain"] == "mock-11111111.example.com"
    assert body["mailbox_health"]["dkim_valid"] is True
    assert body["mailbox_health"]["mock_only"] is True
    assert body["mock_only"] is True
    forbidden = {"tenant_id", "api_key", "secret", "token", "private_key"}
    assert forbidden.isdisjoint(body["mailbox_health"].keys())


def test_outcomes_tenant_summary_returns_safe_dto() -> None:
    fake = _FakeDashboardService()
    resp = _client(fake).get("/api/v1/outcomes")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["outcomes", "mock_only"]
    assert body["outcomes"]["reply_count"] == 10
    assert body["outcomes"]["campaign_id"] is None
    assert body["outcomes"]["mock_only"] is True
    assert body["mock_only"] is True
    assert "tenant_id" not in body["outcomes"]


def test_outcomes_campaign_summary_uses_object_auth_context() -> None:
    fake = _FakeDashboardService(campaign=True)
    resp = _client(fake).get(f"/api/v1/outcomes?campaign_id={_CAMPAIGN}")
    assert resp.status_code == 200
    assert resp.json()["outcomes"]["campaign_id"] == str(_CAMPAIGN)
    assert fake.calls[0]["campaign_id"] == _CAMPAIGN


def test_outcomes_campaign_cross_tenant_fails_closed() -> None:
    fake = _FakeDashboardService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(fake).get(f"/api/v1/outcomes?campaign_id={_CAMPAIGN}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


def test_roi_requires_campaign_id() -> None:
    fake = _FakeDashboardService()
    resp = _client(fake).get("/api/v1/outcomes/roi")
    assert resp.status_code == 422
    assert fake.calls == []


def test_roi_route_uses_object_auth_context() -> None:
    fake = _FakeDashboardService()
    resp = _client(fake).get(f"/api/v1/outcomes/roi?campaign_id={_CAMPAIGN}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["roi"]["campaign_id"] == str(_CAMPAIGN)
    assert body["roi"]["mock_only"] is True
    assert body["mock_only"] is True
    assert "tenant_id" not in body["roi"]
    assert fake.calls[0]["method"] == "get_roi_summary"
    assert fake.calls[0]["campaign_id"] == _CAMPAIGN


def test_mock_event_calls_service_and_returns_mock_only() -> None:
    fake = _FakeDashboardService()
    resp = _client(fake).post("/api/v1/outcomes/mock-events", json=_EVENT_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert body["outcome_event"]["id"] == str(_EVENT)
    assert body["outcome_event"]["campaign_id"] == str(_CAMPAIGN)
    assert body["outcome_event"]["contact_id"] == str(_CONTACT)
    assert body["outcome_event"]["mock_only"] is True
    assert body["mock_only"] is True
    assert "tenant_id" not in body["outcome_event"]
    assert "idempotency_key" not in body["outcome_event"]
    call = fake.calls[0]
    assert call["method"] == "record_mock_outcome_event"
    assert call["principal"].tenant_id == _TENANT
    assert call["campaign_id"] == _CAMPAIGN
    assert call["contact_id"] == _CONTACT
    assert call["idempotency_key"] == "outcome-key-1"


def test_mock_event_duplicate_idempotency_returns_same_safe_response() -> None:
    fake = _FakeDashboardService()
    first = _client(fake).post("/api/v1/outcomes/mock-events", json=_EVENT_BODY, headers=_HEADERS)
    second = _client(fake).post("/api/v1/outcomes/mock-events", json=_EVENT_BODY, headers=_HEADERS)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()


def test_mock_event_invalid_type_maps_to_standard_error() -> None:
    fake = _FakeDashboardService(
        error=AppError(
            "INVALID_OUTCOME_EVENT_TYPE",
            "event_type is not recognised.",
            status_code=400,
        )
    )
    resp = _client(fake).post("/api/v1/outcomes/mock-events", json=_EVENT_BODY, headers=_HEADERS)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_OUTCOME_EVENT_TYPE"


async def test_deliverability_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(deliverability_router, "tenant_session", fake_tenant_session)
    gen = deliverability_router.dashboard_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, deliverability_router.DashboardService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_outcomes_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(outcomes_router, "tenant_session", fake_tenant_session)
    gen = outcomes_router.dashboard_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, outcomes_router.DashboardService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


@pytest.mark.parametrize("module", [deliverability_router, outcomes_router])
def test_dashboard_routers_do_not_import_provider_clients(module: Any) -> None:
    source = inspect.getsource(module).lower()
    forbidden = (
        "sendgrid",
        "mailgun",
        "twilio",
        "stripe",
        "boto3",
        "googleads",
        "google_ads",
        "hubspot",
        "salesforce",
    )
    assert all(term not in source for term in forbidden)
