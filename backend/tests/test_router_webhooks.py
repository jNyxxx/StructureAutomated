"""Webhook route tests for P3-5g."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.routers import webhooks as webhooks_router
from app.services.resend_webhooks import (
    InMemoryResendWebhookEventStore,
    ResendWebhookProcessor,
    ResendWebhookVerifier,
)

_SECRET_BYTES = b"safe-test-webhook-secret"
_SECRET = "whsec_" + base64.b64encode(_SECRET_BYTES).decode("ascii")
_EVENT_ID = "evt_route_safe_123"
_TIMESTAMP = "1760000000"


def _payload(event_type: str = "email.delivered") -> bytes:
    return json.dumps(
        {
            "type": event_type,
            "created_at": "2026-06-28T12:00:00.000Z",
            "data": {"email_id": "email-route-safe-123", "to": ["prospect@example.com"]},
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _signature(raw_body: bytes) -> str:
    signed_payload = b".".join([_EVENT_ID.encode(), _TIMESTAMP.encode(), raw_body])
    digest = hmac.new(_SECRET_BYTES, signed_payload, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode("ascii")


def _headers(raw_body: bytes) -> dict[str, str]:
    return {
        "svix-id": _EVENT_ID,
        "svix-timestamp": _TIMESTAMP,
        "svix-signature": _signature(raw_body),
        "content-type": "application/json",
    }


def _client(secret: str | None = _SECRET) -> TestClient:
    app = create_app()

    def _processor() -> ResendWebhookProcessor:
        return ResendWebhookProcessor(
            verifier=ResendWebhookVerifier(webhook_secret=secret),
            store=InMemoryResendWebhookEventStore(),
        )

    app.dependency_overrides[webhooks_router.resend_webhook_processor] = _processor
    return TestClient(app, raise_server_exceptions=False)


def test_resend_webhook_route_is_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/webhooks/resend" in spec
    assert "post" in spec["/api/v1/webhooks/resend"]


def test_resend_webhook_route_default_dependency_fails_closed() -> None:
    raw_body = _payload()
    resp = TestClient(create_app(), raise_server_exceptions=False).post(
        "/api/v1/webhooks/resend", content=raw_body, headers=_headers(raw_body)
    )

    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "WEBHOOK_SECRET_UNAVAILABLE"


def test_resend_webhook_route_verifies_before_processing() -> None:
    raw_body = _payload()
    bad_headers = _headers(raw_body) | {"svix-signature": "v1,bad"}

    resp = _client().post("/api/v1/webhooks/resend", content=raw_body, headers=bad_headers)

    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "WEBHOOK_SIGNATURE_INVALID"
    serialized = repr(body)
    assert "prospect@example.com" not in serialized
    assert "safe-test-webhook-secret" not in serialized
    assert "v1,bad" not in serialized


def test_resend_webhook_route_returns_safe_normalized_result() -> None:
    raw_body = _payload("email.delivered")

    resp = _client().post("/api/v1/webhooks/resend", content=raw_body, headers=_headers(raw_body))

    assert resp.status_code == 200
    assert resp.json() == {
        "provider": "resend",
        "status": "processed",
        "duplicate": False,
        "event_type": "delivered",
        "mock_only": True,
    }


def test_resend_webhook_route_ignores_open_tracking() -> None:
    raw_body = _payload("email.opened")

    resp = _client().post("/api/v1/webhooks/resend", content=raw_body, headers=_headers(raw_body))

    assert resp.status_code == 200
    assert resp.json() == {
        "provider": "resend",
        "status": "ignored",
        "duplicate": False,
        "event_type": None,
        "mock_only": True,
    }
