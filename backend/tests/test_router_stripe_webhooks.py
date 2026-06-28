"""Stripe webhook route tests for P3-6d."""

from __future__ import annotations

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.routers import webhooks as webhooks_router
from app.services.stripe_webhooks import (
    InMemoryStripeWebhookEventStore,
    StripeWebhookProcessor,
    StripeWebhookVerifier,
)

_SECRET = "whsec_safe_route_webhook_secret"
_EVENT_ID = "evt_route_safe_123"
_TIMESTAMP = "1760000000"


def _payload(event_type: str = "checkout.session.completed") -> bytes:
    return json.dumps(
        {
            "id": _EVENT_ID,
            "object": "event",
            "type": event_type,
            "created": 1760000000,
            "livemode": False,
            "data": {
                "object": {
                    "id": "cs_route_safe_123",
                    "object": "checkout.session",
                    "customer": "cus_route_safe_123",
                    "customer_email": "customer@example.com",
                    "payment_method_details": {"card": {"last4": "4242"}},
                    "tenant_id": "client-supplied-tenant-must-not-be-trusted",
                }
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _signature(raw_body: bytes) -> str:
    signed_payload = b".".join([_TIMESTAMP.encode("utf-8"), raw_body])
    digest = hmac.new(_SECRET.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={_TIMESTAMP},v1={digest}"


def _headers(raw_body: bytes) -> dict[str, str]:
    return {"stripe-signature": _signature(raw_body), "content-type": "application/json"}


def _client(secret: str | None = _SECRET) -> TestClient:
    app = create_app()

    def _processor() -> StripeWebhookProcessor:
        return StripeWebhookProcessor(
            verifier=StripeWebhookVerifier(webhook_secret=secret),
            store=InMemoryStripeWebhookEventStore(),
        )

    app.dependency_overrides[webhooks_router.stripe_webhook_processor] = _processor
    return TestClient(app, raise_server_exceptions=False)


def test_stripe_webhook_route_is_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/webhooks/stripe" in spec
    assert "post" in spec["/api/v1/webhooks/stripe"]


def test_stripe_webhook_route_default_dependency_fails_closed() -> None:
    raw_body = _payload()
    resp = TestClient(create_app(), raise_server_exceptions=False).post(
        "/api/v1/webhooks/stripe", content=raw_body, headers=_headers(raw_body)
    )

    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "STRIPE_WEBHOOK_SECRET_UNAVAILABLE"


def test_stripe_webhook_route_verifies_signature_before_processing() -> None:
    raw_body = _payload()
    bad_headers = _headers(raw_body) | {"stripe-signature": "t=1760000000,v1=bad"}

    resp = _client().post("/api/v1/webhooks/stripe", content=raw_body, headers=bad_headers)

    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "STRIPE_WEBHOOK_SIGNATURE_INVALID"
    serialized = repr(body)
    assert "customer@example.com" not in serialized
    assert "4242" not in serialized
    assert _SECRET not in serialized
    assert "v1=bad" not in serialized


def test_stripe_webhook_route_returns_safe_normalized_result() -> None:
    raw_body = _payload("invoice.payment_succeeded")

    resp = _client().post("/api/v1/webhooks/stripe", content=raw_body, headers=_headers(raw_body))

    assert resp.status_code == 200
    assert resp.json() == {
        "provider": "stripe",
        "status": "processed",
        "duplicate": False,
        "event_type": "invoice.payment_succeeded",
        "mock_only": True,
    }


def test_stripe_webhook_route_ignores_unknown_event() -> None:
    raw_body = _payload("payment_intent.created")

    resp = _client().post("/api/v1/webhooks/stripe", content=raw_body, headers=_headers(raw_body))

    assert resp.status_code == 200
    assert resp.json() == {
        "provider": "stripe",
        "status": "ignored",
        "duplicate": False,
        "event_type": None,
        "mock_only": True,
    }


def test_stripe_webhook_route_does_not_return_client_supplied_tenant_or_payment_data() -> None:
    raw_body = _payload("checkout.session.completed")

    resp = _client().post("/api/v1/webhooks/stripe", content=raw_body, headers=_headers(raw_body))

    assert resp.status_code == 200
    serialized = repr(resp.json())
    assert "client-supplied-tenant" not in serialized
    assert "customer@example.com" not in serialized
    assert "4242" not in serialized
