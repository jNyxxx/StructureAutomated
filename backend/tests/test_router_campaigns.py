"""GET/POST campaign router tests for Phase 2 P2-2."""

import uuid
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.main import create_app
from app.middleware.error_handler import AppError
from app.routers import campaigns as campaigns_router
from app.routers.campaigns import campaign_service
from app.services.campaign import CampaignCreateResult, CampaignRecord

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_OTHER_CAMPAIGN = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_HEADERS = {"Idempotency-Key": "campaign-key-1"}
_BODY = {"name": "Q3 CRE Owners", "description": "Local demo campaign"}


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


def _campaign(campaign_id: uuid.UUID = _CAMPAIGN) -> CampaignRecord:
    return CampaignRecord(
        id=campaign_id,
        tenant_id=_TENANT,
        created_by_user_id=_USER,
        name="Q3 CRE Owners",
        description="Local demo campaign",
        goal="Book calls",
        target_segment="CRE owners",
        notes="Local/mock only",
        status="draft",
    )


class _FakeCampaignService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def list_campaigns(self, **kwargs: Any) -> list[CampaignRecord]:
        self.calls.append({"method": "list_campaigns", **kwargs})
        if self.error is not None:
            raise self.error
        return [_campaign(), _campaign(_OTHER_CAMPAIGN)]

    async def create_campaign(self, **kwargs: Any) -> CampaignCreateResult:
        self.calls.append({"method": "create_campaign", **kwargs})
        if self.error is not None:
            raise self.error
        if self.replay:
            return CampaignCreateResult(campaign=None, idempotency_replay=True)
        return CampaignCreateResult(campaign=_campaign(), idempotency_replay=False)

    async def get_campaign(self, **kwargs: Any) -> CampaignRecord:
        self.calls.append({"method": "get_campaign", **kwargs})
        if self.error is not None:
            raise self.error
        return _campaign()


def _client(service: _FakeCampaignService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        app.dependency_overrides[campaign_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def test_unauthenticated_request_returns_401() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.get("/api/v1/campaigns")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_campaign_routes_are_mounted_under_api_v1() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/campaigns" in spec
    assert "get" in spec["/api/v1/campaigns"]
    assert "post" in spec["/api/v1/campaigns"]
    assert "/api/v1/campaigns/{campaign_id}" in spec
    assert "get" in spec["/api/v1/campaigns/{campaign_id}"]
    assert "patch" not in spec["/api/v1/campaigns/{campaign_id}"]
    assert "/api/v1/campaigns/{campaign_id}/contacts" not in spec


def test_list_campaigns_returns_resource_keyed_body_with_page_metadata() -> None:
    fake = _FakeCampaignService()
    resp = _client(fake).get("/api/v1/campaigns?limit=1")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["campaigns", "page"]
    assert len(body["campaigns"]) == 1
    assert body["campaigns"][0]["id"] == str(_CAMPAIGN)
    assert body["page"] == {"next_cursor": str(_CAMPAIGN), "limit": 1}
    assert fake.calls[0]["method"] == "list_campaigns"
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_create_campaign_requires_idempotency_key() -> None:
    fake = _FakeCampaignService()
    resp = _client(fake).post("/api/v1/campaigns", json=_BODY)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_create_campaign_calls_service_with_tenant_context_and_returns_dto() -> None:
    fake = _FakeCampaignService()
    resp = _client(fake).post("/api/v1/campaigns", json=_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert list(body.keys()) == ["campaign", "idempotency_replay"]
    assert body["campaign"]["id"] == str(_CAMPAIGN)
    assert body["campaign"]["status"] == "draft"
    assert body["idempotency_replay"] is False
    call = fake.calls[0]
    assert call["method"] == "create_campaign"
    assert call["principal"].tenant_id == _TENANT
    assert call["principal"].user_id == _USER
    assert call["name"] == _BODY["name"]
    assert call["idempotency_key"] == "campaign-key-1"


def test_create_campaign_service_error_maps_to_standard_envelope() -> None:
    fake = _FakeCampaignService(
        error=AppError("BILLING_FEATURE_DENIED", "Billing access denied.", status_code=403)
    )
    resp = _client(fake).post("/api/v1/campaigns", json=_BODY, headers=_HEADERS)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "BILLING_FEATURE_DENIED"
    assert "request_id" in body["error"]


def test_create_campaign_idempotency_replay_returns_flag_without_campaign() -> None:
    fake = _FakeCampaignService(replay=True)
    resp = _client(fake).post("/api/v1/campaigns", json=_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    assert resp.json() == {"campaign": None, "idempotency_replay": True}


def test_detail_route_returns_safe_dto() -> None:
    fake = _FakeCampaignService()
    resp = _client(fake).get(f"/api/v1/campaigns/{_CAMPAIGN}")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["campaign"]
    assert body["campaign"]["id"] == str(_CAMPAIGN)
    assert body["campaign"]["name"] == "Q3 CRE Owners"
    assert "metadata" not in resp.text
    assert fake.calls[0]["method"] == "get_campaign"
    assert fake.calls[0]["campaign_id"] == _CAMPAIGN


def test_detail_not_found_or_cross_tenant_policy_uses_standard_envelope() -> None:
    fake = _FakeCampaignService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(fake).get(f"/api/v1/campaigns/{_CAMPAIGN}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


async def test_di_factory_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(campaigns_router, "tenant_session", fake_tenant_session)
    gen = campaigns_router.campaign_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, campaigns_router.CampaignService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
