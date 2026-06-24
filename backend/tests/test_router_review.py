"""Review read router tests for Phase 2 P2-3."""

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
from app.routers.review import review_read_service
from app.services.review_read import ReviewItemPage

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_REVIEW = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_OTHER_REVIEW = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_DRAFT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_CAMPAIGN = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_CONTACT = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
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


def _review(review_id: uuid.UUID = _REVIEW) -> ReviewRecord:
    return ReviewRecord(
        id=review_id,
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="pending_review",
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


def _client(service: _FakeReviewReadService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        app.dependency_overrides[review_read_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/review/items",
        f"/api/v1/review/items/{_REVIEW}",
    ],
)
def test_review_routes_require_authentication(path: str) -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.get(path)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_review_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/review/items" in spec
    assert "get" in spec["/api/v1/review/items"]
    assert "/api/v1/review/items/{review_id}" in spec
    assert "get" in spec["/api/v1/review/items/{review_id}"]


def test_review_queue_list_returns_resource_keyed_body_with_page_metadata() -> None:
    fake = _FakeReviewReadService()
    resp = _client(fake).get(f"/api/v1/review/items?limit=1&campaign_id={_CAMPAIGN}")
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
    resp = _client(fake).get(f"/api/v1/review/items/{_REVIEW}")
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
    resp = _client(fake).get(f"/api/v1/review/items/{_REVIEW}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


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
