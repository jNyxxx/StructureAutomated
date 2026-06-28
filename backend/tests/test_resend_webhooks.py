"""Resend webhook verification and normalization tests for P3-5g."""

from __future__ import annotations

import base64
import hashlib
import hmac
import inspect
import json
from datetime import UTC, datetime

import pytest

from app.middleware.error_handler import AppError
from app.services.resend_webhooks import (
    InMemoryResendWebhookEventStore,
    ResendWebhookProcessor,
    ResendWebhookVerifier,
    normalize_resend_event,
)

_SECRET_BYTES = b"safe-test-webhook-secret"
_SECRET = "whsec_" + base64.b64encode(_SECRET_BYTES).decode("ascii")
_EVENT_ID = "evt_safe_123"
_TIMESTAMP = "1760000000"


def _payload(event_type: str = "email.delivered") -> bytes:
    return json.dumps(
        {
            "type": event_type,
            "created_at": "2026-06-28T12:00:00.000Z",
            "data": {
                "email_id": "email-safe-123",
                "message_id": "message-safe-123",
                "created_at": "2026-06-28T12:00:00.000Z",
                "to": ["prospect@example.com"],
                "from": "AutomatedStructure <outreach@example.com>",
                "subject": "Private subject",
                "bounce": {"type": "Permanent", "subType": "Suppressed", "message": "PII detail"},
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _signature(raw_body: bytes, *, event_id: str = _EVENT_ID, timestamp: str = _TIMESTAMP) -> str:
    signed_payload = b".".join([event_id.encode(), timestamp.encode(), raw_body])
    digest = hmac.new(_SECRET_BYTES, signed_payload, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode("ascii")


def _headers(raw_body: bytes) -> dict[str, str]:
    return {
        "svix-id": _EVENT_ID,
        "svix-timestamp": _TIMESTAMP,
        "svix-signature": _signature(raw_body),
    }


def test_missing_webhook_secret_fails_closed() -> None:
    verifier = ResendWebhookVerifier(webhook_secret=None, secret_ref="secret-ref:webhook")

    with pytest.raises(AppError) as excinfo:
        verifier.verify(raw_body=_payload(), headers=_headers(_payload()))

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.code == "WEBHOOK_SECRET_UNAVAILABLE"
    assert exc.details == {}


def test_invalid_signature_fails_closed_without_leaking_body_or_secret() -> None:
    raw_body = _payload()
    verifier = ResendWebhookVerifier(webhook_secret=_SECRET)
    headers = _headers(raw_body) | {"svix-signature": "v1,invalid"}

    with pytest.raises(AppError) as excinfo:
        verifier.verify(raw_body=raw_body, headers=headers)

    exc = excinfo.value
    serialized = exc.message + repr(exc.details)
    assert exc.status_code == 401
    assert exc.code == "WEBHOOK_SIGNATURE_INVALID"
    assert "prospect@example.com" not in serialized
    assert "safe-test-webhook-secret" not in serialized
    assert "v1,invalid" not in serialized


def test_valid_signature_passes_verification() -> None:
    raw_body = _payload("email.bounced")
    verifier = ResendWebhookVerifier(webhook_secret=_SECRET)

    parsed = verifier.verify(raw_body=raw_body, headers=_headers(raw_body))

    assert parsed["type"] == "email.bounced"
    assert parsed["data"]["email_id"] == "email-safe-123"


@pytest.mark.parametrize(
    ("source_type", "expected"),
    [
        ("email.delivered", "delivered"),
        ("email.bounced", "bounced"),
        ("email.complained", "complained"),
        ("email.delivery_delayed", "deferred"),
        ("email.failed", "failed"),
        ("email.suppressed", "suppressed"),
    ],
)
def test_supported_event_types_normalize_to_safe_internal_shape(
    source_type: str, expected: str
) -> None:
    payload = json.loads(_payload(source_type))

    event = normalize_resend_event(payload=payload, provider_event_id=_EVENT_ID)

    assert event is not None
    assert event.provider == "resend"
    assert event.provider_event_id == _EVENT_ID
    assert event.provider_message_id == "email-safe-123"
    assert event.event_type == expected
    assert event.occurred_at == datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    serialized = repr(event)
    assert "prospect@example.com" not in serialized
    assert "Private subject" not in serialized
    assert "PII detail" not in serialized


def test_bounce_metadata_keeps_only_safe_bounce_labels() -> None:
    payload = json.loads(_payload("email.bounced"))

    event = normalize_resend_event(payload=payload, provider_event_id=_EVENT_ID)

    assert event is not None
    assert event.safe_metadata == {
        "source_type": "email.bounced",
        "bounce_type": "Permanent",
        "bounce_subtype": "Suppressed",
    }


@pytest.mark.parametrize("source_type", ["email.opened", "email.clicked"])
def test_open_click_tracking_events_are_ignored(source_type: str) -> None:
    payload = json.loads(_payload(source_type))

    assert normalize_resend_event(payload=payload, provider_event_id=_EVENT_ID) is None


@pytest.mark.parametrize("source_type", ["domain.created", "contact.created", "email.unknown"])
def test_unknown_or_non_email_delivery_events_are_ignored(source_type: str) -> None:
    payload = json.loads(_payload(source_type))

    assert normalize_resend_event(payload=payload, provider_event_id=_EVENT_ID) is None


async def test_duplicate_provider_event_id_is_idempotent() -> None:
    raw_body = _payload("email.delivered")
    processor = ResendWebhookProcessor(
        verifier=ResendWebhookVerifier(webhook_secret=_SECRET),
        store=InMemoryResendWebhookEventStore(),
    )

    first = await processor.process(raw_body=raw_body, headers=_headers(raw_body))
    second = await processor.process(raw_body=raw_body, headers=_headers(raw_body))

    assert first.status == "processed"
    assert first.duplicate is False
    assert second.status == "duplicate"
    assert second.duplicate is True
    assert second.event_type == "delivered"


def test_resend_webhook_source_has_no_resend_sdk_or_api_calls() -> None:
    from app.services import resend_webhooks

    source = inspect.getsource(resend_webhooks).lower()
    forbidden = (
        "api.resend",
        "resend.com",
        "emails.send",
        "from resend",
        "import resend",
        "requests.",
        "httpx.",
    )
    for marker in forbidden:
        assert marker not in source
