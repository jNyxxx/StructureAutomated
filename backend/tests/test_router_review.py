"""Review read/action router tests for Phase 2 P2-3/P2-3b."""

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
from app.repositories.review_repo import ReviewRecord
from app.routers import review as review_router
from app.routers.review import review_action_service, review_read_service
from app.services.review import ReviewActionResult
from app.services.review_read import ReviewItemPage

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_REVIEW = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_OTHER_REVIEW = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_DRAFT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_CAMPAIGN = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_CONTACT = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "review-action-key-1"}
_REASON_BODY = {"reason": "Needs revision"}


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


def _review(review_id: uuid.UUID = _REVIEW, *, status: str = "pending_review") -> ReviewRecord:
    return ReviewRecord(
        id=review_id,
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status=status,
        reviewer_user_id=None,
        action_reason=None,
        reviewed_at=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


class _FakeReviewReadService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def list_items(self, **kwargs: Any) -> ReviewItemPage:
        self.calls.append({"method": "list_items", **kwargs})
        if self.error is not None:
            raise self.error
        return ReviewItemPage(
            items=(_review(), _review(_OTHER_REVIEW)),
            next_cursor=str(_REVIEW),
            limit=kwargs["limit"],
        )

    async def get_item(self, **kwargs: Any) -> ReviewRecord:
        self.calls.append({"method": "get_item", **kwargs})
        if self.error is not None:
            raise self.error
        return _review()


class _FakeReviewActionService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def approve_draft_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> ReviewActionResult:
        self.calls.append({"method": "approve_draft_idempotent", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        if self.replay:
            return ReviewActionResult(review_item=None, idempotency_replay=True)
        return ReviewActionResult(review_item=_review(status="approved"), idempotency_replay=False)

    async def reject_draft_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> ReviewActionResult:
        self.calls.append({"method": "reject_draft_idempotent", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        if self.replay:
            return ReviewActionResult(review_item=None, idempotency_replay=True)
        return ReviewActionResult(review_item=_review(status="rejected"), idempotency_replay=False)

    async def request_regeneration_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> ReviewActionResult:
        self.calls.append(
            {"method": "request_regeneration_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        if self.replay:
            return ReviewActionResult(review_item=None, idempotency_replay=True)
        return ReviewActionResult(
            review_item=_review(status="regeneration_requested"), idempotency_replay=False
        )


def _client(
    read_service: _FakeReviewReadService | None = None,
    action_service: _FakeReviewActionService | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if read_service is not None:
        app.dependency_overrides[review_read_service] = lambda: read_service
    if action_service is not None:
        app.dependency_overrides[review_action_service] = lambda: action_service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("get", "/api/v1/review/items", None, None),
        ("get", f"/api/v1/review/items/{_REVIEW}", None, None),
        ("post", f"/api/v1/review/items/{_REVIEW}/approve", None, _HEADERS),
        ("post", f"/api/v1/review/items/{_REVIEW}/reject", _REASON_BODY, _HEADERS),
        (
            "post",
            f"/api/v1/review/items/{_REVIEW}/request-regeneration",
            _REASON_BODY,
            _HEADERS,
        ),
    ],
)
def test_review_routes_require_authentication(
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    headers: dict[str, str] | None,
) -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.request(method, path, json=json_body, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_review_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/review/items" in spec
    assert "get" in spec["/api/v1/review/items"]
    assert "/api/v1/review/items/{review_id}" in spec
    assert "get" in spec["/api/v1/review/items/{review_id}"]
    assert "/api/v1/review/items/{review_id}/approve" in spec
    assert "post" in spec["/api/v1/review/items/{review_id}/approve"]
    assert "/api/v1/review/items/{review_id}/reject" in spec
    assert "post" in spec["/api/v1/review/items/{review_id}/reject"]
    assert "/api/v1/review/items/{review_id}/request-regeneration" in spec
    assert "post" in spec["/api/v1/review/items/{review_id}/request-regeneration"]


def test_review_queue_list_returns_resource_keyed_body_with_page_metadata() -> None:
    fake = _FakeReviewReadService()
    resp = _client(read_service=fake).get(f"/api/v1/review/items?limit=1&campaign_id={_CAMPAIGN}")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["review_items", "page"]
    assert len(body["review_items"]) == 2
    assert body["review_items"][0]["id"] == str(_REVIEW)
    assert body["review_items"][0]["status"] == "pending_review"
    assert body["page"] == {"next_cursor": str(_REVIEW), "limit": 1}
    call = fake.calls[0]
    assert call["method"] == "list_items"
    assert call["principal"].tenant_id == _TENANT
    assert call["campaign_id"] == _CAMPAIGN
    assert call["status"] is None


def test_review_item_detail_returns_safe_dto() -> None:
    fake = _FakeReviewReadService()
    resp = _client(read_service=fake).get(f"/api/v1/review/items/{_REVIEW}")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["review_item"]
    assert body["review_item"]["id"] == str(_REVIEW)
    assert body["review_item"]["draft_id"] == str(_DRAFT)
    assert body["review_item"]["campaign_id"] == str(_CAMPAIGN)
    assert "metadata" not in resp.text
    call = fake.calls[0]
    assert call["method"] == "get_item"
    assert call["review_id"] == _REVIEW


def test_missing_or_cross_tenant_review_item_uses_standard_policy() -> None:
    fake = _FakeReviewReadService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(read_service=fake).get(f"/api/v1/review/items/{_REVIEW}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


@pytest.mark.parametrize(
    ("path", "json_body"),
    [
        (f"/api/v1/review/items/{_REVIEW}/approve", None),
        (f"/api/v1/review/items/{_REVIEW}/reject", _REASON_BODY),
        (f"/api/v1/review/items/{_REVIEW}/request-regeneration", _REASON_BODY),
    ],
)
def test_review_actions_require_idempotency_key(
    path: str, json_body: dict[str, Any] | None
) -> None:
    fake = _FakeReviewActionService()
    resp = _client(action_service=fake).post(path, json=json_body)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_approve_calls_service_with_tenant_context_and_returns_safe_dto() -> None:
    fake = _FakeReviewActionService()
    resp = _client(action_service=fake).post(
        f"/api/v1/review/items/{_REVIEW}/approve", headers=_HEADERS
    )
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["review_item", "idempotency_replay"]
    assert body["review_item"]["id"] == str(_REVIEW)
    assert body["review_item"]["status"] == "approved"
    assert body["idempotency_replay"] is False
    call = fake.calls[0]
    assert call["method"] == "approve_draft_idempotent"
    assert call["principal"].tenant_id == _TENANT
    assert call["review_id"] == _REVIEW
    assert call["idempotency_key"] == "review-action-key-1"


def test_approve_error_maps_to_standard_envelope() -> None:
    fake = _FakeReviewActionService(
        error=AppError("SAFETY_GATE_FAILED", "Safety gate failed.", status_code=400)
    )
    resp = _client(action_service=fake).post(
        f"/api/v1/review/items/{_REVIEW}/approve", headers=_HEADERS
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "SAFETY_GATE_FAILED"


def test_reject_calls_service_with_reason_and_tenant_context() -> None:
    fake = _FakeReviewActionService()
    resp = _client(action_service=fake).post(
        f"/api/v1/review/items/{_REVIEW}/reject", json=_REASON_BODY, headers=_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["review_item"]["status"] == "rejected"
    call = fake.calls[0]
    assert call["method"] == "reject_draft_idempotent"
    assert call["principal"].tenant_id == _TENANT
    assert call["review_id"] == _REVIEW
    assert call["reason"] == "Needs revision"
    assert call["idempotency_key"] == "review-action-key-1"


def test_request_regeneration_calls_service_with_reason_and_tenant_context() -> None:
    fake = _FakeReviewActionService()
    resp = _client(action_service=fake).post(
        f"/api/v1/review/items/{_REVIEW}/request-regeneration",
        json=_REASON_BODY,
        headers=_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["review_item"]["status"] == "regeneration_requested"
    call = fake.calls[0]
    assert call["method"] == "request_regeneration_idempotent"
    assert call["principal"].tenant_id == _TENANT
    assert call["review_id"] == _REVIEW
    assert call["reason"] == "Needs revision"
    assert call["idempotency_key"] == "review-action-key-1"


def test_review_action_idempotency_replay_returns_safe_response() -> None:
    fake = _FakeReviewActionService(replay=True)
    resp = _client(action_service=fake).post(
        f"/api/v1/review/items/{_REVIEW}/approve", headers=_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json() == {"review_item": None, "idempotency_replay": True}


async def test_review_read_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(review_router, "tenant_session", fake_tenant_session)
    gen = review_router.review_read_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, review_router.ReviewReadService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_review_action_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(review_router, "tenant_session", fake_tenant_session)
    gen = review_router.review_action_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, review_router.ReviewService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


def test_review_router_does_not_import_send_gate_or_providers() -> None:
    source = inspect.getsource(review_router).lower()
    assert "send_gate" not in source
    assert "smtp" not in source
    assert "boto3" not in source
    assert "mailgun" not in source
