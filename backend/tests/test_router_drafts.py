"""Draft router tests for Phase 2 P2-3."""

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
from app.repositories.draft_repo import DraftEvidenceRecord, DraftRecord
from app.routers import drafts as drafts_router
from app.routers.drafts import draft_generation_service, draft_read_service
from app.services.draft_generation import DraftCreateResult
from app.services.draft_read import DraftEvidencePage

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_DRAFT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_EVIDENCE = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_SOURCE = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "draft-key-1"}
_BODY = {"campaign_id": str(_CAMPAIGN), "contact_id": str(_CONTACT)}


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


def _draft() -> DraftRecord:
    return DraftRecord(
        id=_DRAFT,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro subject",
        body="Draft body",
        idempotency_key="stored-key-not-exposed",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _evidence() -> DraftEvidenceRecord:
    return DraftEvidenceRecord(
        id=_EVIDENCE,
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        source_type="knowledge_chunk",
        source_id=_SOURCE,
        content_snippet="Safe evidence snippet",
        created_at=_NOW,
    )


class _FakeDraftGenerationService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def generate_draft(self, **kwargs: Any) -> DraftCreateResult:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        if self.replay:
            return DraftCreateResult(draft=None, idempotency_replay=True)
        return DraftCreateResult(draft=_draft(), idempotency_replay=False)


class _FakeDraftReadService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def get_draft(self, **kwargs: Any) -> DraftRecord:
        self.calls.append({"method": "get_draft", **kwargs})
        if self.error is not None:
            raise self.error
        return _draft()

    async def list_evidence(self, **kwargs: Any) -> DraftEvidencePage:
        self.calls.append({"method": "list_evidence", **kwargs})
        if self.error is not None:
            raise self.error
        return DraftEvidencePage(items=(_evidence(),), next_cursor=None, limit=kwargs["limit"])


def _client(
    gen_service: _FakeDraftGenerationService | None = None,
    read_service: _FakeDraftReadService | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if gen_service is not None:
        app.dependency_overrides[draft_generation_service] = lambda: gen_service
    if read_service is not None:
        app.dependency_overrides[draft_read_service] = lambda: read_service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("post", "/api/v1/drafts/generate", _BODY, _HEADERS),
        ("get", f"/api/v1/drafts/{_DRAFT}", None, None),
        ("get", f"/api/v1/drafts/{_DRAFT}/evidence", None, None),
    ],
)
def test_draft_routes_require_authentication(
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    headers: dict[str, str] | None,
) -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.request(method, path, json=json_body, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_draft_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/drafts/generate" in spec
    assert "post" in spec["/api/v1/drafts/generate"]
    assert "/api/v1/drafts/{draft_id}" in spec
    assert "get" in spec["/api/v1/drafts/{draft_id}"]
    assert "/api/v1/drafts/{draft_id}/evidence" in spec
    assert "get" in spec["/api/v1/drafts/{draft_id}/evidence"]


def test_generate_draft_requires_idempotency_key() -> None:
    fake = _FakeDraftGenerationService()
    resp = _client(gen_service=fake).post("/api/v1/drafts/generate", json=_BODY)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_generate_draft_calls_service_with_tenant_context_and_returns_safe_dto() -> None:
    fake = _FakeDraftGenerationService()
    resp = _client(gen_service=fake).post("/api/v1/drafts/generate", json=_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert list(body.keys()) == ["draft", "idempotency_replay"]
    assert body["draft"]["id"] == str(_DRAFT)
    assert body["draft"]["subject"] == "Intro subject"
    assert body["draft"]["body"] == "Draft body"
    assert body["idempotency_replay"] is False
    assert "idempotency_key" not in resp.text
    call = fake.calls[0]
    assert call["principal"].tenant_id == _TENANT
    assert call["principal"].user_id == _USER
    assert call["campaign_id"] == _CAMPAIGN
    assert call["contact_id"] == _CONTACT
    assert call["idempotency_key"] == "draft-key-1"


def test_generate_draft_service_error_maps_to_standard_envelope() -> None:
    fake = _FakeDraftGenerationService(
        error=AppError("SAFETY_GATE_FAILED", "Safety gate failed.", status_code=400)
    )
    resp = _client(gen_service=fake).post("/api/v1/drafts/generate", json=_BODY, headers=_HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "SAFETY_GATE_FAILED"
    assert "request_id" in body["error"]


def test_generate_draft_idempotency_replay_returns_flag_without_draft() -> None:
    fake = _FakeDraftGenerationService(replay=True)
    resp = _client(gen_service=fake).post("/api/v1/drafts/generate", json=_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    assert resp.json() == {"draft": None, "idempotency_replay": True}


def test_draft_detail_returns_safe_dto() -> None:
    fake = _FakeDraftReadService()
    resp = _client(read_service=fake).get(f"/api/v1/drafts/{_DRAFT}")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["draft"]
    assert body["draft"]["id"] == str(_DRAFT)
    assert body["draft"]["status"] == "generated"
    assert "idempotency_key" not in resp.text
    assert fake.calls[0]["method"] == "get_draft"
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_draft_evidence_returns_resource_keyed_body_with_page_metadata() -> None:
    fake = _FakeDraftReadService()
    resp = _client(read_service=fake).get(f"/api/v1/drafts/{_DRAFT}/evidence?limit=1")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["evidence", "page"]
    assert body["evidence"][0]["id"] == str(_EVIDENCE)
    assert body["evidence"][0]["content_snippet"] == "Safe evidence snippet"
    assert body["page"] == {"next_cursor": None, "limit": 1}
    assert fake.calls[0]["method"] == "list_evidence"


def test_missing_or_cross_tenant_draft_uses_standard_policy() -> None:
    fake = _FakeDraftReadService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(read_service=fake).get(f"/api/v1/drafts/{_DRAFT}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


async def test_draft_generation_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(drafts_router, "tenant_session", fake_tenant_session)
    gen = drafts_router.draft_generation_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, drafts_router.DraftGenerationService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
