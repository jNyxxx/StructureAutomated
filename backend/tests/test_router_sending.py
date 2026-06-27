"""Sending router tests for Phase 2 P2-4 mock/local APIs."""

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
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.repositories.sending_repo import OutboundMessageRecord, SendGateResultRecord
from app.routers import sending as sending_router
from app.routers.sending import mock_sender_service, outbound_read_service, send_gate_service
from app.services.mock_sender import MockSendIntentResult, MockSendResult
from app.services.outbound_read import OutboundMessagePage
from app.services.rate_limit import RateLimitService
from app.services.send_gate import SendGateDryRunResult

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_DRAFT = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_GATE = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_MESSAGE = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_OTHER_MESSAGE = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "send-key-1"}
_BODY = {"draft_id": str(_DRAFT)}


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


def _gate(status: str = "passed") -> SendGateResultRecord:
    return SendGateResultRecord(
        id=_GATE,
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        status=status,
        deny_reason_code=None if status == "passed" else "review_not_approved",
        created_at=_NOW,
    )


def _message(message_id: uuid.UUID = _MESSAGE, status: str = "mock_sent") -> OutboundMessageRecord:
    return OutboundMessageRecord(
        id=message_id,
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        status=status,
        sent_at=_NOW if status == "mock_sent" else None,
        created_at=_NOW,
        updated_at=_NOW,
    )


class _FakeSendGateService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def evaluate_gate_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> SendGateDryRunResult:
        self.calls.append({"principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        if self.replay:
            return SendGateDryRunResult(gate_result=None, idempotency_replay=True)
        return SendGateDryRunResult(gate_result=_gate(), idempotency_replay=False)


class _FakeMockSenderService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def send_approved_draft_idempotent(
        self, principal: CurrentPrincipal, **kwargs: Any
    ) -> MockSendIntentResult:
        self.calls.append({"principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        if self.replay:
            return MockSendIntentResult(result=None, idempotency_replay=True)
        return MockSendIntentResult(
            result=MockSendResult(
                outbound_message_id=_MESSAGE,
                status="mock_sent",
                sent_at=_NOW,
                mock_only=True,
            ),
            idempotency_replay=False,
        )


class _FakeOutboundReadService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def list_messages(self, **kwargs: Any) -> OutboundMessagePage:
        self.calls.append({"method": "list_messages", **kwargs})
        if self.error is not None:
            raise self.error
        return OutboundMessagePage(
            items=(_message(), _message(_OTHER_MESSAGE, status="blocked")),
            next_cursor=str(_MESSAGE),
            limit=kwargs["limit"],
        )

    async def get_message(self, **kwargs: Any) -> OutboundMessageRecord:
        self.calls.append({"method": "get_message", **kwargs})
        if self.error is not None:
            raise self.error
        return _message()


def _client(
    gate_service: _FakeSendGateService | None = None,
    sender_service: _FakeMockSenderService | None = None,
    read_service: _FakeOutboundReadService | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if gate_service is not None:
        app.dependency_overrides[send_gate_service] = lambda: gate_service
    if sender_service is not None:
        app.dependency_overrides[mock_sender_service] = lambda: sender_service
    if read_service is not None:
        app.dependency_overrides[outbound_read_service] = lambda: read_service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("post", "/api/v1/send-gate/dry-run", _BODY, _HEADERS),
        ("post", "/api/v1/send-intents", _BODY, _HEADERS),
        ("get", "/api/v1/outbound-messages", None, None),
        ("get", f"/api/v1/outbound-messages/{_MESSAGE}", None, None),
    ],
)
def test_sending_routes_require_authentication(
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    headers: dict[str, str] | None,
) -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.request(method, path, json=json_body, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_sending_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/send-gate/dry-run" in spec
    assert "post" in spec["/api/v1/send-gate/dry-run"]
    assert "/api/v1/send-intents" in spec
    assert "post" in spec["/api/v1/send-intents"]
    assert "/api/v1/outbound-messages" in spec
    assert "get" in spec["/api/v1/outbound-messages"]
    assert "/api/v1/outbound-messages/{message_id}" in spec
    assert "get" in spec["/api/v1/outbound-messages/{message_id}"]


@pytest.mark.parametrize(
    "path",
    ["/api/v1/send-gate/dry-run", "/api/v1/send-intents"],
)
def test_post_sending_routes_require_idempotency_key(path: str) -> None:
    gate = _FakeSendGateService()
    sender = _FakeMockSenderService()
    resp = _client(gate_service=gate, sender_service=sender).post(path, json=_BODY)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert gate.calls == []
    assert sender.calls == []


def test_dry_run_calls_service_with_tenant_context_and_returns_safe_dto() -> None:
    gate = _FakeSendGateService()
    resp = _client(gate_service=gate).post(
        "/api/v1/send-gate/dry-run", json=_BODY, headers=_HEADERS
    )
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["send_gate_result", "idempotency_replay", "mock_only"]
    assert body["send_gate_result"]["id"] == str(_GATE)
    assert body["send_gate_result"]["status"] == "passed"
    assert body["send_gate_result"]["mock_only"] is True
    assert body["mock_only"] is True
    call = gate.calls[0]
    assert call["principal"].tenant_id == _TENANT
    assert call["principal"].user_id == _USER
    assert call["draft_id"] == _DRAFT
    assert call["idempotency_key"] == "send-key-1"


def test_dry_run_gate_denial_maps_to_standard_envelope() -> None:
    gate = _FakeSendGateService(
        error=AppError("REVIEW_NOT_APPROVED", "Draft has not been reviewed.", status_code=400)
    )
    resp = _client(gate_service=gate).post(
        "/api/v1/send-gate/dry-run", json=_BODY, headers=_HEADERS
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "REVIEW_NOT_APPROVED"


def test_send_intent_calls_mock_sender_with_tenant_context_and_mock_only_response() -> None:
    sender = _FakeMockSenderService()
    resp = _client(sender_service=sender).post("/api/v1/send-intents", json=_BODY, headers=_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert list(body.keys()) == ["result", "idempotency_replay", "mock_only"]
    assert body["result"]["outbound_message_id"] == str(_MESSAGE)
    assert body["result"]["status"] == "mock_sent"
    assert body["result"]["mock_only"] is True
    assert body["mock_only"] is True
    call = sender.calls[0]
    assert call["principal"].tenant_id == _TENANT
    assert call["draft_id"] == _DRAFT
    assert call["idempotency_key"] == "send-key-1"


def test_send_intent_rate_limit_blocks_101st_request_and_preserves_counter() -> None:
    sender = _FakeMockSenderService()
    client = _client(sender_service=sender)

    responses = [
        client.post(
            "/api/v1/send-intents",
            json=_BODY,
            headers={"Idempotency-Key": f"send-key-{idx}"},
        )
        for idx in range(101)
    ]

    assert [resp.status_code for resp in responses[:100]] == [201] * 100
    assert responses[100].status_code == 429
    assert responses[100].json()["error"]["code"] == "RATE_LIMITED"
    assert len(sender.calls) == 100


def test_send_intent_duplicate_maps_to_409() -> None:
    sender = _FakeMockSenderService(
        error=AppError("DUPLICATE_SEND", "Duplicate send blocked.", status_code=409)
    )
    resp = _client(sender_service=sender).post(
        "/api/v1/send-intents",
        json=_BODY,
        headers=_HEADERS,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE_SEND"


def test_send_intent_idempotency_replay_returns_safe_response() -> None:
    sender = _FakeMockSenderService(replay=True)
    resp = _client(sender_service=sender).post(
        "/api/v1/send-intents",
        json=_BODY,
        headers=_HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json() == {"result": None, "idempotency_replay": True, "mock_only": True}


def test_outbound_list_returns_resource_keyed_body_with_page_metadata() -> None:
    read = _FakeOutboundReadService()
    resp = _client(read_service=read).get("/api/v1/outbound-messages?limit=1")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["outbound_messages", "page", "mock_only"]
    assert len(body["outbound_messages"]) == 2
    assert body["outbound_messages"][0]["id"] == str(_MESSAGE)
    assert body["outbound_messages"][0]["mock_only"] is True
    assert body["page"] == {"next_cursor": str(_MESSAGE), "limit": 1}
    assert body["mock_only"] is True
    call = read.calls[0]
    assert call["method"] == "list_messages"
    assert call["principal"].tenant_id == _TENANT


def test_outbound_detail_returns_safe_dto() -> None:
    read = _FakeOutboundReadService()
    resp = _client(read_service=read).get(f"/api/v1/outbound-messages/{_MESSAGE}")
    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["outbound_message", "mock_only"]
    assert body["outbound_message"]["id"] == str(_MESSAGE)
    assert body["outbound_message"]["status"] == "mock_sent"
    assert body["outbound_message"]["mock_only"] is True
    assert "contact_hash" not in resp.text
    call = read.calls[0]
    assert call["method"] == "get_message"
    assert call["message_id"] == _MESSAGE


def test_cross_tenant_or_missing_outbound_message_fails_closed() -> None:
    read = _FakeOutboundReadService(
        error=AppError("OBJECT_ACCESS_DENIED", "Object not found.", status_code=403)
    )
    resp = _client(read_service=read).get(f"/api/v1/outbound-messages/{_MESSAGE}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OBJECT_ACCESS_DENIED"


async def test_send_gate_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(sending_router, "tenant_session", fake_tenant_session)
    gen = sending_router.send_gate_service(
        _principal(), RateLimitService(InMemoryRateLimitBackend())
    )
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, sending_router.SendGateService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_mock_sender_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(sending_router, "tenant_session", fake_tenant_session)
    gen = sending_router.mock_sender_service(
        _principal(), RateLimitService(InMemoryRateLimitBackend())
    )
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, sending_router.MockSenderService)
    assert service._followups is None  # noqa: SLF001
    assert service._email_provider.kind == "mock"  # noqa: SLF001
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_outbound_read_di_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(sending_router, "tenant_session", fake_tenant_session)
    gen = sending_router.outbound_read_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, sending_router.OutboundReadService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


def test_sending_router_does_not_import_provider_clients() -> None:
    source = inspect.getsource(sending_router).lower()
    assert "sendgrid" not in source
    assert "mailgun" not in source
    assert "twilio" not in source
    assert "boto3" not in source
    assert "smtplib" not in source
