"""GET contacts/prospects router tests for Phase 2 P2-1b."""

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
from app.routers import contacts as contacts_router
from app.routers.contacts import contact_read_service
from app.services.contact_read import ContactReadPage, ContactReadRecord

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)


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


def _record() -> ContactReadRecord:
    return ContactReadRecord(
        id=_CONTACT,
        tenant_id=_TENANT,
        full_name="Jane Owner",
        title="Founder",
        email="jane@example.com",
        domain="example.com",
        company_name="Example CRE",
        created_at=_NOW,
        updated_at=_NOW,
    )


class _FakeContactReadService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def list_contacts(self, **kwargs: Any) -> ContactReadPage:
        self.calls.append({"method": "list_contacts", **kwargs})
        if self.error is not None:
            raise self.error
        return ContactReadPage(items=(_record(),), next_cursor="cursor-2", limit=25)

    async def list_prospects(self, **kwargs: Any) -> ContactReadPage:
        self.calls.append({"method": "list_prospects", **kwargs})
        if self.error is not None:
            raise self.error
        return ContactReadPage(items=(_record(),), next_cursor=None, limit=25)

    async def get_contact(self, **kwargs: Any) -> ContactReadRecord:
        self.calls.append({"method": "get_contact", **kwargs})
        if self.error is not None:
            raise self.error
        return _record()


def _client(service: _FakeContactReadService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        app.dependency_overrides[contact_read_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def test_unauthenticated_request_returns_401() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.get("/api/v1/contacts")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_contact_and_prospect_routes_are_mounted_under_api_v1() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/prospects" in spec
    assert "/api/v1/contacts" in spec
    assert "/api/v1/contacts/{contact_id}" in spec


def test_contacts_list_response_is_resource_keyed_with_page_metadata() -> None:
    fake = _FakeContactReadService()
    resp = _client(fake).get("/api/v1/contacts?limit=25")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["contacts", "page"]
    assert body["contacts"][0]["id"] == str(_CONTACT)
    assert body["page"] == {"next_cursor": "cursor-2", "limit": 25}
    assert fake.calls[0]["method"] == "list_contacts"
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_prospects_response_is_contact_projection_with_page_metadata() -> None:
    fake = _FakeContactReadService()
    resp = _client(fake).get("/api/v1/prospects")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["prospects", "page"]
    assert body["prospects"][0]["id"] == str(_CONTACT)
    assert body["prospects"][0]["contact_id"] == str(_CONTACT)
    assert body["page"] == {"next_cursor": None, "limit": 25}
    assert fake.calls[0]["method"] == "list_prospects"


def test_contact_detail_response_returns_contact_dto() -> None:
    fake = _FakeContactReadService()
    resp = _client(fake).get(f"/api/v1/contacts/{_CONTACT}")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["contact"]
    assert body["contact"]["id"] == str(_CONTACT)
    assert body["contact"]["full_name"] == "Jane Owner"
    assert body["contact"]["email"] == "jane@example.com"
    assert "dedupe_hash" not in resp.text
    assert "metadata" not in resp.text
    assert fake.calls[0]["method"] == "get_contact"
    assert fake.calls[0]["contact_id"] == _CONTACT


def test_service_app_error_maps_to_standard_envelope() -> None:
    fake = _FakeContactReadService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(fake).get(f"/api/v1/contacts/{_CONTACT}")
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "OBJECT_ACCESS_DENIED"
    assert "request_id" in body["error"]


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

    monkeypatch.setattr(contacts_router, "tenant_session", fake_tenant_session)
    gen = contacts_router.contact_read_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, contacts_router.ContactReadService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
