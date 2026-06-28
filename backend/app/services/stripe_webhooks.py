"""Stripe webhook verification and normalization foundation.

P3-6d verifies Stripe-style webhook signatures using an injected endpoint
secret, normalizes only safe billing event references, and records idempotency
through a narrow repository boundary. It uses no Stripe package, provider API,
raw payload persistence, tenant billing-state mutation, checkout session, or
money movement.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from app.middleware.error_handler import AppError

STRIPE_PROVIDER = "stripe"
STRIPE_SIGNATURE_HEADER = "stripe-signature"

NormalizedStripeEventType = Literal[
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "customer.subscription.trial_will_end",
    "charge.refunded",
    "charge.dispute.created",
]
StripeWebhookProcessStatus = Literal["processed", "duplicate", "ignored"]

_SUPPORTED_EVENT_TYPES: set[NormalizedStripeEventType] = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "customer.subscription.trial_will_end",
    "charge.refunded",
    "charge.dispute.created",
}


@dataclass(frozen=True)
class StripeWebhookSignatureParts:
    """Safe subset extracted from the Stripe-Signature header."""

    timestamp: str
    signatures: tuple[str, ...]


@dataclass(frozen=True)
class NormalizedStripeWebhookEvent:
    """PII-minimized internal billing event shape."""

    provider: str
    provider_event_id: str
    event_type: NormalizedStripeEventType
    occurred_at: datetime
    safe_object_refs: Mapping[str, str] = field(default_factory=dict)
    safe_metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StripeWebhookProcessingResult:
    """Webhook processing result returned to the route layer."""

    provider: str
    status: StripeWebhookProcessStatus
    duplicate: bool = False
    event_type: NormalizedStripeEventType | None = None
    provider_event_id: str | None = None


class StripeWebhookEventStore(Protocol):
    """Idempotency boundary for normalized Stripe webhook events."""

    async def mark_processed(self, *, provider_event_id: str) -> bool:
        """Return True for first processing, False for duplicate event IDs."""


class InMemoryStripeWebhookEventStore:
    """Process-local foundation store used until DB persistence is approved."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    async def mark_processed(self, *, provider_event_id: str) -> bool:
        if provider_event_id in self._seen:
            return False
        self._seen.add(provider_event_id)
        return True


class StripeWebhookVerifier:
    """Verify Stripe webhook signatures without SDK or network calls."""

    def __init__(self, *, webhook_secret: str | None, secret_ref: str | None = None) -> None:
        self._webhook_secret = webhook_secret
        self._secret_ref = secret_ref

    def verify(self, *, raw_body: bytes, headers: Mapping[str, str]) -> dict[str, Any]:
        if not self._webhook_secret:
            raise AppError(
                "STRIPE_WEBHOOK_SECRET_UNAVAILABLE",
                "Stripe webhook verification is not available.",
                status_code=503,
            )
        signature_header = _extract_signature_header(headers)
        if not _valid_signature(
            secret=self._webhook_secret,
            raw_body=raw_body,
            signature_header=signature_header,
        ):
            raise AppError(
                "STRIPE_WEBHOOK_SIGNATURE_INVALID",
                "Stripe webhook signature is invalid.",
                status_code=401,
            )
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError(
                "STRIPE_WEBHOOK_PAYLOAD_INVALID",
                "Stripe webhook payload is invalid.",
                status_code=400,
            ) from exc
        if not isinstance(parsed, dict):
            raise AppError(
                "STRIPE_WEBHOOK_PAYLOAD_INVALID",
                "Stripe webhook payload is invalid.",
                status_code=400,
            )
        return parsed


def normalize_stripe_event(payload: Mapping[str, Any]) -> NormalizedStripeWebhookEvent | None:
    """Normalize a verified Stripe payload into a safe internal event.

    Unknown event types are ignored safely instead of being trusted or persisted.
    """
    provider_event_id = _safe_str(payload.get("id"))
    raw_type = payload.get("type")
    if provider_event_id is None or not isinstance(raw_type, str):
        raise AppError(
            "STRIPE_WEBHOOK_PAYLOAD_INVALID",
            "Stripe webhook payload is invalid.",
            status_code=400,
        )
    if raw_type not in _SUPPORTED_EVENT_TYPES:
        return None

    raw_data = payload.get("data")
    data = raw_data if isinstance(raw_data, Mapping) else {}
    raw_object = data.get("object")
    stripe_object = raw_object if isinstance(raw_object, Mapping) else {}
    event_type = raw_type
    occurred_at = _parse_created(payload.get("created")) or datetime.now(UTC)
    return NormalizedStripeWebhookEvent(
        provider=STRIPE_PROVIDER,
        provider_event_id=provider_event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        safe_object_refs=_safe_object_refs(stripe_object),
        safe_metadata=_safe_metadata(payload=payload, stripe_object=stripe_object),
    )


class StripeWebhookProcessor:
    """Verify, normalize, and dedupe Stripe webhook events."""

    def __init__(self, *, verifier: StripeWebhookVerifier, store: StripeWebhookEventStore) -> None:
        self._verifier = verifier
        self._store = store

    async def process(
        self, *, raw_body: bytes, headers: Mapping[str, str]
    ) -> StripeWebhookProcessingResult:
        payload = self._verifier.verify(raw_body=raw_body, headers=headers)
        normalized = normalize_stripe_event(payload)
        provider_event_id = _safe_str(payload.get("id"))
        if normalized is None:
            return StripeWebhookProcessingResult(
                provider=STRIPE_PROVIDER,
                status="ignored",
                provider_event_id=provider_event_id,
            )
        first_seen = await self._store.mark_processed(
            provider_event_id=normalized.provider_event_id
        )
        if not first_seen:
            return StripeWebhookProcessingResult(
                provider=STRIPE_PROVIDER,
                status="duplicate",
                duplicate=True,
                event_type=normalized.event_type,
                provider_event_id=normalized.provider_event_id,
            )
        return StripeWebhookProcessingResult(
            provider=STRIPE_PROVIDER,
            status="processed",
            event_type=normalized.event_type,
            provider_event_id=normalized.provider_event_id,
        )


def _extract_signature_header(headers: Mapping[str, str]) -> str:
    lowered = {key.lower(): value for key, value in headers.items()}
    signature = lowered.get(STRIPE_SIGNATURE_HEADER)
    if not signature:
        raise AppError(
            "STRIPE_WEBHOOK_SIGNATURE_MISSING",
            "Stripe webhook signature is required.",
            status_code=401,
        )
    return signature.strip()


def _valid_signature(*, secret: str, raw_body: bytes, signature_header: str) -> bool:
    parts = _parse_signature_header(signature_header)
    signed_payload = b".".join([parts.timestamp.encode("utf-8"), raw_body])
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(candidate, expected) for candidate in parts.signatures)


def _parse_signature_header(signature_header: str) -> StripeWebhookSignatureParts:
    timestamp: str | None = None
    signatures: list[str] = []
    for item in signature_header.split(","):
        key, separator, value = item.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if key == "t" and value:
            timestamp = value
        elif key == "v1" and value:
            signatures.append(value)
    if not timestamp or not signatures:
        raise AppError(
            "STRIPE_WEBHOOK_SIGNATURE_MISSING",
            "Stripe webhook signature is required.",
            status_code=401,
        )
    return StripeWebhookSignatureParts(timestamp=timestamp, signatures=tuple(signatures))


def _parse_created(value: object) -> datetime | None:
    if isinstance(value, int):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, float):
        return datetime.fromtimestamp(value, tz=UTC)
    return None


def _safe_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _safe_object_refs(stripe_object: Mapping[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    for key in (
        "id",
        "object",
        "customer",
        "subscription",
        "invoice",
        "payment_intent",
        "price",
        "product",
    ):
        value = _safe_str(stripe_object.get(key))
        if value is not None:
            refs[key] = value
    return refs


def _safe_metadata(
    *, payload: Mapping[str, Any], stripe_object: Mapping[str, Any]
) -> dict[str, str]:
    metadata: dict[str, str] = {}
    object_type = _safe_str(stripe_object.get("object"))
    api_version = _safe_str(payload.get("api_version"))
    livemode = payload.get("livemode")
    if object_type is not None:
        metadata["object_type"] = object_type
    if api_version is not None:
        metadata["api_version"] = api_version
    if isinstance(livemode, bool):
        metadata["livemode"] = str(livemode).lower()
    return metadata
