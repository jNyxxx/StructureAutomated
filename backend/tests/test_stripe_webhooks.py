"""Stripe webhook verification and normalization tests for P3-6d."""

from __future__ import annotations

import hashlib
import hmac
import inspect
import json
from datetime import UTC, datetime

import pytest

from app.middleware.error_handler import AppError
from app.services.stripe_webhooks import (
    InMemoryStripeWebhookEventStore,
    StripeWebhookProcessor,
    StripeWebhookVerifier,
    normalize_stripe_event,
)

_SECRET = "whsec_safe_test_webhook_secret"
_EVENT_ID = "evt_safe_123"
_TIMESTAMP = "1760000000"


def _payload(event_type: str = "checkout.session.completed") -> bytes:
    return json.dumps(
        {
            "id": _EVENT_ID,
            "object": "event",
            "type": event_type,
            "created": 1760000000,
            "livemode": False,
            "api_version": "2026-01-01",
            "data": {
                "object": {
                    "id": "cs_test_safe_123",
                    "object": "checkout.session",
                    "customer": "cus_safe_123",
                    "subscription": "sub_safe_123",
                    "invoice": "in_safe_123",
                    "payment_intent": "pi_safe_123",
                    "customer_email": "customer@example.com",
                    "billing_details": {"email": "customer@example.com"},
                    "payment_method_details": {"card": {"last4": "4242"}},
                }
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _signature(raw_body: bytes, *, timestamp: str = _TIMESTAMP) -> str:
    signed_payload = b".".join([timestamp.encode("utf-8"), raw_body])
    digest = hmac.new(_SECRET.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _headers(raw_body: bytes) -> dict[str, str]:
    return {"stripe-signature": _signature(raw_body)}


def test_missing_stripe_webhook_secret_fails_closed() -> None:
    raw_body = _payload()
    verifier = StripeWebhookVerifier(webhook_secret=None, secret_ref="secret-ref:billing/webhook")

    with pytest.raises(AppError) as excinfo:
        verifier.verify(raw_body=raw_body, headers=_headers(raw_body))

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.code == "STRIPE_WEBHOOK_SECRET_UNAVAILABLE"
    assert exc.details == {}


def test_missing_signature_header_fails_closed() -> None:
    raw_body = _payload()
    verifier = StripeWebhookVerifier(webhook_secret=_SECRET)

    with pytest.raises(AppError) as excinfo:
        verifier.verify(raw_body=raw_body, headers={})

    exc = excinfo.value
    assert exc.status_code == 401
    assert exc.code == "STRIPE_WEBHOOK_SIGNATURE_MISSING"


def test_invalid_signature_fails_closed_without_leaking_sensitive_values() -> None:
    raw_body = _payload()
    verifier = StripeWebhookVerifier(webhook_secret=_SECRET)

    with pytest.raises(AppError) as excinfo:
        verifier.verify(raw_body=raw_body, headers={"stripe-signature": "t=1760000000,v1=bad"})

    exc = excinfo.value
    serialized = exc.message + repr(exc.details)
    assert exc.status_code == 401
    assert exc.code == "STRIPE_WEBHOOK_SIGNATURE_INVALID"
    assert "customer@example.com" not in serialized
    assert "4242" not in serialized
    assert _SECRET not in serialized
    assert "v1=bad" not in serialized


def test_valid_signed_fixture_passes_verification() -> None:
    raw_body = _payload("invoice.payment_failed")
    verifier = StripeWebhookVerifier(webhook_secret=_SECRET)

    parsed = verifier.verify(raw_body=raw_body, headers=_headers(raw_body))

    assert parsed["id"] == _EVENT_ID
    assert parsed["type"] == "invoice.payment_failed"


@pytest.mark.parametrize(
    "event_type",
    [
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
        "customer.subscription.trial_will_end",
        "charge.refunded",
        "charge.dispute.created",
    ],
)
def test_supported_event_types_normalize_to_safe_internal_shape(event_type: str) -> None:
    payload = json.loads(_payload(event_type))

    event = normalize_stripe_event(payload)

    assert event is not None
    assert event.provider == "stripe"
    assert event.provider_event_id == _EVENT_ID
    assert event.event_type == event_type
    assert event.occurred_at == datetime.fromtimestamp(1760000000, tz=UTC)
    assert event.safe_object_refs == {
        "id": "cs_test_safe_123",
        "object": "checkout.session",
        "customer": "cus_safe_123",
        "subscription": "sub_safe_123",
        "invoice": "in_safe_123",
        "payment_intent": "pi_safe_123",
    }
    assert event.safe_metadata == {
        "object_type": "checkout.session",
        "api_version": "2026-01-01",
        "livemode": "false",
    }
    serialized = repr(event)
    assert "customer@example.com" not in serialized
    assert "4242" not in serialized
    assert "payment_method_details" not in serialized
    assert "billing_details" not in serialized


def test_unknown_event_type_is_ignored() -> None:
    payload = json.loads(_payload("payment_intent.created"))

    assert normalize_stripe_event(payload) is None


async def test_duplicate_provider_event_id_is_idempotent() -> None:
    raw_body = _payload("invoice.payment_succeeded")
    processor = StripeWebhookProcessor(
        verifier=StripeWebhookVerifier(webhook_secret=_SECRET),
        store=InMemoryStripeWebhookEventStore(),
    )

    first = await processor.process(raw_body=raw_body, headers=_headers(raw_body))
    second = await processor.process(raw_body=raw_body, headers=_headers(raw_body))

    assert first.status == "processed"
    assert first.duplicate is False
    assert second.status == "duplicate"
    assert second.duplicate is True
    assert second.event_type == "invoice.payment_succeeded"


def test_stripe_webhook_source_has_no_sdk_api_network_or_billing_mutation_markers() -> None:
    from app.services import stripe_webhooks

    source = inspect.getsource(stripe_webhooks).lower()
    forbidden = (
        "import stripe",
        "from stripe",
        "stripe.",
        "api.stripe",
        "checkout.sessions.create",
        "billing_portal",
        "payment_intents.create",
        "requests.",
        "httpx.",
        "tenant_status",
        "update_subscription",
        "transition_subscription",
    )
    for marker in forbidden:
        assert marker not in source
