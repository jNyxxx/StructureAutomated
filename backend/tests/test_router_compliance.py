"""Router tests for Phase 2 P2-6 mock/local compliance and suppression APIs."""

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
from app.routers import compliance as compliance_router
from app.routers.compliance import compliance_api_service
from app.services.compliance import ComplianceProfileRecord, SuppressionRecord
from app.services.compliance_api import (
    ComplianceProfileActionResult,
    SuppressionActionResult,
    SuppressionPage,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_SUPPRESSION = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "safe-key-1"}
_RAW_EMAIL = "Buyer@Example.COM"
_SUPPRESSION_BODY = {
    "channel": "email",
    "contact_identifier": _RAW_EMAIL,
    "reason": "unsubscribe",
    "source": "manual",
    "never_contact": True,
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


def _profile() -> ComplianceProfileRecord:
    return ComplianceProfileRecord(
        tenant_id=_TENANT,
        jurisdiction="US",
        sending_review_required=True,
        live_sending_allowed=False,
        sms_allowed=False,
    )


def _suppression(*, revoked: bool = False) -> SuppressionRecord:
    return SuppressionRecord(
        id=_SUPPRESSION,
        tenant_id=_TENANT,
        channel="email",
        contact_hash="f" * 64,
        reason="unsubscribe",
        source="manual",
        never_contact=True,
        created_at=_NOW,
        revoked_at=_NOW if revoked else None,
    )


class _FakeComplianceAPIService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def get_profile(self, principal: CurrentPrincipal) -> ComplianceProfileRecord:
        self.calls.append({"method": "get_profile", "principal": principal})
        if self.error is not None:
            raise self.error
        return _profile()

    async def update_profile_idempotent(
        self,
        principal: CurrentPrincipal,
        **kwargs: Any,
    ) -> ComplianceProfileActionResult:
        self.calls.append({"method": "update_profile_idempotent", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        if kwargs.get("live_sending_allowed"):
            raise AppError(
                "LIVE_SENDING_DEFERRED",
                "Live sending remains deferred during the local/mock MVP.",
                status_code=400,
            )
        if kwargs.get("sms_allowed"):
            raise AppError(
                "SMS_COMPLIANCE_DEFERRED",
                "SMS remains deferred during the local/mock MVP.",
                status_code=400,
            )
        return ComplianceProfileActionResult(profile=_profile(), idempotency_replay=self.replay)

    async def list_suppressions(
        self,
        principal: CurrentPrincipal,
        **kwargs: Any,
    ) -> SuppressionPage:
        self.calls.append({"method": "list_suppressions", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        return SuppressionPage(items=(_suppression(),), next_cursor=None, limit=kwargs["limit"])

    async def add_suppression_idempotent(
        self,
        principal: CurrentPrincipal,
        **kwargs: Any,
    ) -> SuppressionActionResult:
        self.calls.append(
            {"method": "add_suppression_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        return SuppressionActionResult(suppression=_suppression(), idempotency_replay=self.replay)

    async def reinstate_suppression_idempotent(
        self,
        principal: CurrentPrincipal,
        **kwargs: Any,
    ) -> SuppressionActionResult:
        self.calls.append(
            {"method": "reinstate_suppression_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        return SuppressionActionResult(
            suppression=_suppression(revoked=True), idempotency_replay=self.replay
        )


def _client(service: _FakeComplianceAPIService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        app.dependency_overrides[compliance_api_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("get", "/api/v1/compliance/profile", None, None),
        ("put", "/api/v1/compliance/profile", {"jurisdiction": "US"}, _HEADERS),
        ("get", "/api/v1/suppressions", None, None),
        ("post", "/api/v1/suppressions", _SUPPRESSION_BODY, _HEADERS),
        ("post", f"/api/v1/suppressions/{_SUPPRESSION}/reinstate", None, _HEADERS),
    ],
)
def test_compliance_routes_require_authentication(
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


def test_compliance_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/compliance/profile" in spec
    assert "get" in spec["/api/v1/compliance/profile"]
    assert "put" in spec["/api/v1/compliance/profile"]
    assert "/api/v1/suppressions" in spec
    assert "get" in spec["/api/v1/suppressions"]
    assert "post" in spec["/api/v1/suppressions"]
    assert "/api/v1/suppressions/{suppression_id}/reinstate" in spec
    assert "post" in spec["/api/v1/suppressions/{suppression_id}/reinstate"]


def test_get_compliance_profile_returns_default_safe_profile() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).get("/api/v1/compliance/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["compliance_profile"] == {
        "jurisdiction": "US",
        "sending_review_required": True,
        "live_sending_allowed": False,
        "sms_allowed": False,
        "mock_only": True,
    }
    assert body["mock_only"] is True
    assert "tenant_id" not in body["compliance_profile"]
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_put_compliance_profile_requires_idempotency_key() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).put("/api/v1/compliance/profile", json={"jurisdiction": "US"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"jurisdiction": "US", "live_sending_allowed": True}, "LIVE_SENDING_DEFERRED"),
        ({"jurisdiction": "US", "sms_allowed": True}, "SMS_COMPLIANCE_DEFERRED"),
    ],
)
def test_put_compliance_profile_rejects_live_send_and_sms(body: dict[str, Any], code: str) -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).put("/api/v1/compliance/profile", json=body, headers=_HEADERS)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == code


def test_put_compliance_profile_calls_service_with_principal_context() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).put(
        "/api/v1/compliance/profile",
        json={"jurisdiction": "US", "sending_review_required": True},
        headers=_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["compliance_profile"]["mock_only"] is True
    assert body["idempotency_replay"] is False
    assert fake.calls[0]["method"] == "update_profile_idempotent"
    assert fake.calls[0]["principal"].tenant_id == _TENANT
    assert fake.calls[0]["idempotency_key"] == "safe-key-1"


def test_list_suppressions_returns_safe_dtos_without_hash_or_identifier() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).get("/api/v1/suppressions")
    assert resp.status_code == 200
    body = resp.json()
    item = body["suppressions"][0]
    assert item["id"] == str(_SUPPRESSION)
    assert item["channel"] == "email"
    assert item["active"] is True
    assert item["mock_only"] is True
    assert body["mock_only"] is True
    assert "contact_hash" not in item
    assert "contact_identifier" not in item
    assert _RAW_EMAIL not in str(body)


def test_create_suppression_requires_idempotency_key() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).post("/api/v1/suppressions", json=_SUPPRESSION_BODY)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_create_suppression_does_not_echo_raw_identifier() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).post("/api/v1/suppressions", json=_SUPPRESSION_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    item = body["suppression"]
    assert item["id"] == str(_SUPPRESSION)
    assert item["mock_only"] is True
    assert body["mock_only"] is True
    assert body["idempotency_replay"] is False
    assert "contact_hash" not in item
    assert "contact_identifier" not in item
    assert _RAW_EMAIL not in str(body)
    assert fake.calls[0]["contact_identifier"] == _RAW_EMAIL


def test_create_suppression_duplicate_idempotency_is_safe() -> None:
    fake = _FakeComplianceAPIService(replay=True)
    first = _client(fake).post("/api/v1/suppressions", json=_SUPPRESSION_BODY, headers=_HEADERS)
    second = _client(fake).post("/api/v1/suppressions", json=_SUPPRESSION_BODY, headers=_HEADERS)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()
    assert first.json()["idempotency_replay"] is True


def test_reinstate_requires_idempotency_key() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).post(f"/api/v1/suppressions/{_SUPPRESSION}/reinstate")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_reinstate_cross_tenant_or_missing_fails_closed() -> None:
    fake = _FakeComplianceAPIService(
        error=AppError("SUPPRESSION_NOT_FOUND", "Suppression not found.", status_code=403)
    )
    resp = _client(fake).post(f"/api/v1/suppressions/{_SUPPRESSION}/reinstate", headers=_HEADERS)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SUPPRESSION_NOT_FOUND"


def test_reinstate_returns_safe_revoked_dto() -> None:
    fake = _FakeComplianceAPIService()
    resp = _client(fake).post(f"/api/v1/suppressions/{_SUPPRESSION}/reinstate", headers=_HEADERS)
    assert resp.status_code == 200
    item = resp.json()["suppression"]
    assert item["active"] is False
    assert item["revoked_at"] is not None
    assert "contact_hash" not in item
    assert "contact_identifier" not in item


async def test_compliance_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(compliance_router, "tenant_session", fake_tenant_session)
    gen = compliance_router.compliance_api_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, compliance_router.ComplianceAPIService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


def test_compliance_router_does_not_import_provider_clients() -> None:
    source = inspect.getsource(compliance_router).lower()
    forbidden = (
        "sendgrid",
        "mailgun",
        "twilio",
        "stripe",
        "boto3",
        "hubspot",
        "salesforce",
    )
    assert all(term not in source for term in forbidden)
