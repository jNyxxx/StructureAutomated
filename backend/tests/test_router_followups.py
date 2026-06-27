"""Follow-up router tests for Phase 2 P2-4b mock/local APIs."""

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
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.repositories.followup_repo import FollowUpRuleRecord, FollowUpScheduleRecord
from app.routers import followups as followups_router
from app.routers.followups import followup_service
from app.services.followup_scheduler import (
    FollowUpActionResult,
    FollowUpRulePage,
    FollowUpSchedulePage,
)
from app.services.rate_limit import RateLimitService

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_RULE = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_SCHEDULE = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_MESSAGE = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
_DRAFT = uuid.UUID("99999999-9999-9999-9999-999999999999")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "followup-key-1"}
_RULE_BODY = {"campaign_id": str(_CAMPAIGN), "delay_seconds": 86400}
_SCHEDULE_BODY = {"original_outbound_message_id": str(_MESSAGE)}


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


def _rule(rule_id: uuid.UUID = _RULE) -> FollowUpRuleRecord:
    return FollowUpRuleRecord(
        id=rule_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        delay_seconds=86400,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _schedule(status: str = "scheduled") -> FollowUpScheduleRecord:
    return FollowUpScheduleRecord(
        id=_SCHEDULE,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        original_outbound_message_id=_MESSAGE,
        original_draft_id=_DRAFT,
        followup_rule_id=_RULE,
        status=status,
        run_after=_NOW + timedelta(days=1),
        actor_user_id=_USER,
        actor_role="owner",
        created_at=_NOW,
        updated_at=_NOW,
    )


class _FakeFollowUpService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def list_followup_rules(self, **kwargs: Any) -> FollowUpRulePage:
        self.calls.append({"method": "list_followup_rules", **kwargs})
        if self.error is not None:
            raise self.error
        return FollowUpRulePage(items=(_rule(),), next_cursor=str(_RULE), limit=kwargs["limit"])

    async def create_followup_rule_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> FollowUpActionResult:
        self.calls.append(
            {"method": "create_followup_rule_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        if self.replay:
            return FollowUpActionResult(record=None, idempotency_replay=True)
        return FollowUpActionResult(record=_rule(), idempotency_replay=False)

    async def list_followup_schedules(self, **kwargs: Any) -> FollowUpSchedulePage:
        self.calls.append({"method": "list_followup_schedules", **kwargs})
        if self.error is not None:
            raise self.error
        return FollowUpSchedulePage(
            items=(_schedule(),), next_cursor=str(_SCHEDULE), limit=kwargs["limit"]
        )

    async def create_manual_schedule_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> FollowUpActionResult:
        self.calls.append(
            {"method": "create_manual_schedule_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        if self.replay:
            return FollowUpActionResult(record=None, idempotency_replay=True)
        return FollowUpActionResult(record=_schedule(), idempotency_replay=False)

    async def mock_run_schedule_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> FollowUpActionResult:
        self.calls.append(
            {"method": "mock_run_schedule_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        if self.replay:
            return FollowUpActionResult(record=None, idempotency_replay=True)
        return FollowUpActionResult(record=_schedule(status="mock_sent"), idempotency_replay=False)


def _client(service: _FakeFollowUpService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        app.dependency_overrides[followup_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("get", "/api/v1/followups/rules", None, None),
        ("post", "/api/v1/followups/rules", _RULE_BODY, _HEADERS),
        ("get", "/api/v1/followups/schedules", None, None),
        ("post", "/api/v1/followups/schedules", _SCHEDULE_BODY, _HEADERS),
        ("post", f"/api/v1/followups/schedules/{_SCHEDULE}/mock-run", None, _HEADERS),
    ],
)
def test_followup_routes_require_authentication(
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    headers: dict[str, str] | None,
) -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.request(method, path, json=json_body, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_followup_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/followups/rules" in spec
    assert "get" in spec["/api/v1/followups/rules"]
    assert "post" in spec["/api/v1/followups/rules"]
    assert "/api/v1/followups/schedules" in spec
    assert "get" in spec["/api/v1/followups/schedules"]
    assert "post" in spec["/api/v1/followups/schedules"]
    assert "/api/v1/followups/schedules/{schedule_id}/mock-run" in spec
    assert "post" in spec["/api/v1/followups/schedules/{schedule_id}/mock-run"]


@pytest.mark.parametrize(
    ("path", "json_body"),
    [
        ("/api/v1/followups/rules", _RULE_BODY),
        ("/api/v1/followups/schedules", _SCHEDULE_BODY),
        (f"/api/v1/followups/schedules/{_SCHEDULE}/mock-run", None),
    ],
)
def test_followup_post_routes_require_idempotency_key(
    path: str, json_body: dict[str, Any] | None
) -> None:
    fake = _FakeFollowUpService()
    resp = _client(fake).post(path, json=json_body)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


def test_rule_list_returns_resource_keyed_body_with_page_metadata() -> None:
    fake = _FakeFollowUpService()
    resp = _client(fake).get("/api/v1/followups/rules?limit=1")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["followup_rules", "page", "mock_only"]
    assert body["followup_rules"][0]["id"] == str(_RULE)
    assert body["followup_rules"][0]["mock_only"] is True
    assert body["page"] == {"next_cursor": str(_RULE), "limit": 1}
    assert body["mock_only"] is True
    assert fake.calls[0]["principal"].tenant_id == _TENANT


def test_rule_create_calls_service_with_tenant_context() -> None:
    fake = _FakeFollowUpService()
    resp = _client(fake).post("/api/v1/followups/rules", json=_RULE_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert body["followup_rule"]["id"] == str(_RULE)
    assert body["followup_rule"]["mock_only"] is True
    assert body["mock_only"] is True
    call = fake.calls[0]
    assert call["method"] == "create_followup_rule_idempotent"
    assert call["principal"].tenant_id == _TENANT
    assert call["campaign_id"] == _CAMPAIGN
    assert call["delay_seconds"] == 86400
    assert call["idempotency_key"] == "followup-key-1"


def test_followup_mutation_rate_limit_blocks_61st_request() -> None:
    fake = _FakeFollowUpService()
    client = _client(fake)

    responses = [
        client.post(
            "/api/v1/followups/rules",
            json=_RULE_BODY,
            headers={"Idempotency-Key": f"followup-key-{idx}"},
        )
        for idx in range(61)
    ]

    assert [resp.status_code for resp in responses[:60]] == [201] * 60
    assert responses[60].status_code == 429
    assert responses[60].json()["error"]["code"] == "RATE_LIMITED"
    assert len(fake.calls) == 60


def test_rule_create_duplicate_maps_to_409() -> None:
    fake = _FakeFollowUpService(
        error=AppError("DUPLICATE_RULE", "Duplicate rule.", status_code=409)
    )
    resp = _client(fake).post("/api/v1/followups/rules", json=_RULE_BODY, headers=_HEADERS)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE_RULE"


def test_schedule_list_returns_resource_keyed_body_with_page_metadata() -> None:
    fake = _FakeFollowUpService()
    resp = _client(fake).get("/api/v1/followups/schedules?limit=1")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["followup_schedules", "page", "mock_only"]
    assert body["followup_schedules"][0]["id"] == str(_SCHEDULE)
    assert body["followup_schedules"][0]["status"] == "scheduled"
    assert body["followup_schedules"][0]["mock_only"] is True
    assert body["page"] == {"next_cursor": str(_SCHEDULE), "limit": 1}
    assert body["mock_only"] is True


def test_schedule_create_calls_service_and_returns_mock_only_response() -> None:
    fake = _FakeFollowUpService()
    resp = _client(fake).post("/api/v1/followups/schedules", json=_SCHEDULE_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert body["followup_schedule"]["id"] == str(_SCHEDULE)
    assert body["followup_schedule"]["status"] == "scheduled"
    assert body["mock_only"] is True
    call = fake.calls[0]
    assert call["method"] == "create_manual_schedule_idempotent"
    assert call["principal"].tenant_id == _TENANT
    assert call["outbound_message_id"] == _MESSAGE
    assert call["idempotency_key"] == "followup-key-1"


def test_schedule_create_duplicate_maps_to_409() -> None:
    fake = _FakeFollowUpService(
        error=AppError("DUPLICATE_FOLLOWUP", "Duplicate followup.", status_code=409)
    )
    resp = _client(fake).post("/api/v1/followups/schedules", json=_SCHEDULE_BODY, headers=_HEADERS)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE_FOLLOWUP"


def test_mock_run_calls_service_and_returns_mock_sent() -> None:
    fake = _FakeFollowUpService()
    resp = _client(fake).post(f"/api/v1/followups/schedules/{_SCHEDULE}/mock-run", headers=_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["followup_schedule"]["status"] == "mock_sent"
    assert body["followup_schedule"]["mock_only"] is True
    assert body["mock_only"] is True
    call = fake.calls[0]
    assert call["method"] == "mock_run_schedule_idempotent"
    assert call["principal"].tenant_id == _TENANT
    assert call["schedule_id"] == _SCHEDULE
    assert call["idempotency_key"] == "followup-key-1"


def test_mock_run_skipped_gate_failure_returns_skipped_status() -> None:
    class _SkippedFollowUpService(_FakeFollowUpService):
        async def mock_run_schedule_idempotent(
            self, principal: CurrentPrincipal, **kwargs: Any
        ) -> FollowUpActionResult:
            self.calls.append(
                {"method": "mock_run_schedule_idempotent", "principal": principal, **kwargs}
            )
            return FollowUpActionResult(
                record=_schedule(status="skipped"),
                idempotency_replay=False,
            )

    fake = _SkippedFollowUpService()
    resp = _client(fake).post(f"/api/v1/followups/schedules/{_SCHEDULE}/mock-run", headers=_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["followup_schedule"]["status"] == "skipped"


def test_idempotency_replay_returns_safe_response() -> None:
    fake = _FakeFollowUpService(replay=True)
    resp = _client(fake).post("/api/v1/followups/rules", json=_RULE_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    assert resp.json() == {"followup_rule": None, "idempotency_replay": True, "mock_only": True}


def test_cross_tenant_or_missing_schedule_fails_closed() -> None:
    fake = _FakeFollowUpService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(fake).get("/api/v1/followups/schedules")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


async def test_followup_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(followups_router, "tenant_session", fake_tenant_session)
    gen = followups_router.followup_service(
        _principal(), RateLimitService(InMemoryRateLimitBackend())
    )
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, followups_router.FollowUpSchedulerService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


def test_followup_router_does_not_import_provider_clients() -> None:
    source = inspect.getsource(followups_router).lower()
    assert "sendgrid" not in source
    assert "mailgun" not in source
    assert "twilio" not in source
    assert "boto3" not in source
