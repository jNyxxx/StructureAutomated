"""Resend webhook verification and normalization foundation.

P3-5g verifies Svix-style Resend webhook signatures using an injected secret,
normalizes only safe event fields, and records idempotency through a narrow
repository boundary. It does not import the Resend SDK, call Resend, persist raw
payloads, or trigger delivery behavior.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from app.middleware.error_handler import AppError

RESEND_PROVIDER = "resend"
SVIX_ID_HEADER = "svix-id"
SVIX_TIMESTAMP_HEADER = "svix-timestamp"
SVIX_SIGNATURE_HEADER = "svix-signature"

NormalizedResendEventType = Literal[
    "delivered",
    "bounced",
    "complained",
    "deferred",
    "failed",
    "suppressed",
]
WebhookProcessStatus = Literal["processed", "duplicate", "ignored"]

_EVENT_TYPE_MAP: dict[str, NormalizedResendEventType] = {
    "email.delivered": "delivered",
    "email.bounced": "bounced",
    "email.complained": "complained",
    "email.delivery_delayed": "deferred",
    "email.failed": "failed",
    "email.suppressed": "suppressed",
}
_DISABLED_EVENT_TYPES = {"email.opened", "email.clicked"}
_IGNORED_PREFIXES = ("domain.", "contact.")


@dataclass(frozen=True)
class ResendWebhookHeaders:
    """Safe header subset required for signature verification."""

    event_id: str
    timestamp: str
    signature: str


@dataclass(frozen=True)
class NormalizedResendWebhookEvent:
    """PII-minimized internal event shape."""

    provider: str
    provider_event_id: str
    provider_message_id: str | None
    event_type: NormalizedResendEventType
    occurred_at: datetime
    safe_metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResendWebhookProcessingResult:
    """Webhook processing result returned to the route layer."""

    provider: str
    status: WebhookProcessStatus
    duplicate: bool = False
    event_type: NormalizedResendEventType | None = None
    provider_event_id: str | None = None


class ResendWebhookEventStore(Protocol):
    """Idempotency boundary for normalized webhook events."""

    async def mark_processed(self, *, provider_event_id: str) -> bool:
        """Return True for first processing, False for duplicate event IDs."""


class InMemoryResendWebhookEventStore:
    """Process-local foundation store used until DB persistence is approved."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    async def mark_processed(self, *, provider_event_id: str) -> bool:
        if provider_event_id in self._seen:
            return False
        self._seen.add(provider_event_id)
        return True


class ResendWebhookVerifier:
    """Verify Resend/Svix webhook signatures without SDK or network calls."""

    def __init__(self, *, webhook_secret: str | None, secret_ref: str | None = None) -> None:
        self._webhook_secret = webhook_secret
        self._secret_ref = secret_ref

    def verify(self, *, raw_body: bytes, headers: Mapping[str, str]) -> dict[str, Any]:
        if not self._webhook_secret:
            raise AppError(
                "WEBHOOK_SECRET_UNAVAILABLE",
                "Webhook verification is not available.",
                status_code=503,
            )
        safe_headers = _extract_headers(headers)
        if not _valid_signature(
            secret=self._webhook_secret,
            event_id=safe_headers.event_id,
            timestamp=safe_headers.timestamp,
            raw_body=raw_body,
            signature_header=safe_headers.signature,
        ):
            raise AppError(
                "WEBHOOK_SIGNATURE_INVALID",
                "Webhook signature is invalid.",
                status_code=401,
            )
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError(
                "WEBHOOK_PAYLOAD_INVALID",
                "Webhook payload is invalid.",
                status_code=400,
            ) from exc
        if not isinstance(parsed, dict):
            raise AppError(
                "WEBHOOK_PAYLOAD_INVALID",
                "Webhook payload is invalid.",
                status_code=400,
            )
        return parsed


def normalize_resend_event(
    *, payload: Mapping[str, Any], provider_event_id: str
) -> NormalizedResendWebhookEvent | None:
    """Normalize a verified Resend payload into a safe internal event.

    Open/click tracking is intentionally ignored in P3-5g. Unknown event types
    are ignored safely instead of being trusted or persisted.
    """
    raw_type = payload.get("type")
    if not isinstance(raw_type, str):
        raise AppError("WEBHOOK_PAYLOAD_INVALID", "Webhook payload is invalid.", status_code=400)
    if raw_type in _DISABLED_EVENT_TYPES:
        return None
    if raw_type.startswith(_IGNORED_PREFIXES):
        return None
    event_type = _EVENT_TYPE_MAP.get(raw_type)
    if event_type is None:
        return None

    raw_data = payload.get("data")
    data = raw_data if isinstance(raw_data, Mapping) else {}
    occurred_at = _parse_timestamp(payload.get("created_at")) or _parse_timestamp(
        data.get("created_at")
    )
    provider_message_id = _safe_str(data.get("email_id")) or _safe_str(data.get("message_id"))
    metadata = _safe_metadata(raw_type=raw_type, event_type=event_type, data=data)
    return NormalizedResendWebhookEvent(
        provider=RESEND_PROVIDER,
        provider_event_id=provider_event_id,
        provider_message_id=provider_message_id,
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(UTC),
        safe_metadata=metadata,
    )


class ResendWebhookProcessor:
    """Verify, normalize, and dedupe Resend webhook events."""

    def __init__(self, *, verifier: ResendWebhookVerifier, store: ResendWebhookEventStore) -> None:
        self._verifier = verifier
        self._store = store

    async def process(
        self, *, raw_body: bytes, headers: Mapping[str, str]
    ) -> ResendWebhookProcessingResult:
        safe_headers = _extract_headers(headers)
        payload = self._verifier.verify(raw_body=raw_body, headers=headers)
        normalized = normalize_resend_event(
            payload=payload,
            provider_event_id=safe_headers.event_id,
        )
        if normalized is None:
            return ResendWebhookProcessingResult(
                provider=RESEND_PROVIDER,
                status="ignored",
                provider_event_id=safe_headers.event_id,
            )
        first_seen = await self._store.mark_processed(
            provider_event_id=normalized.provider_event_id
        )
        if not first_seen:
            return ResendWebhookProcessingResult(
                provider=RESEND_PROVIDER,
                status="duplicate",
                duplicate=True,
                event_type=normalized.event_type,
                provider_event_id=normalized.provider_event_id,
            )
        return ResendWebhookProcessingResult(
            provider=RESEND_PROVIDER,
            status="processed",
            event_type=normalized.event_type,
            provider_event_id=normalized.provider_event_id,
        )


def _extract_headers(headers: Mapping[str, str]) -> ResendWebhookHeaders:
    lowered = {key.lower(): value for key, value in headers.items()}
    event_id = lowered.get(SVIX_ID_HEADER)
    timestamp = lowered.get(SVIX_TIMESTAMP_HEADER)
    signature = lowered.get(SVIX_SIGNATURE_HEADER)
    if not event_id or not timestamp or not signature:
        raise AppError(
            "WEBHOOK_SIGNATURE_MISSING",
            "Webhook signature is required.",
            status_code=401,
        )
    return ResendWebhookHeaders(
        event_id=event_id.strip(),
        timestamp=timestamp.strip(),
        signature=signature.strip(),
    )


def _valid_signature(
    *, secret: str, event_id: str, timestamp: str, raw_body: bytes, signature_header: str
) -> bool:
    if not event_id or not timestamp or not signature_header:
        return False
    secret_bytes = _secret_bytes(secret)
    signed_payload = b".".join([event_id.encode("utf-8"), timestamp.encode("utf-8"), raw_body])
    digest = hmac.new(secret_bytes, signed_payload, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    for candidate in signature_header.split():
        if not candidate.startswith("v1,"):
            continue
        supplied = candidate.removeprefix("v1,").strip()
        if hmac.compare_digest(supplied, expected):
            return True
    return False


def _secret_bytes(secret: str) -> bytes:
    raw = secret.strip()
    if raw.startswith("whsec_"):
        encoded = raw.removeprefix("whsec_")
        try:
            return base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            return raw.encode("utf-8")
    return raw.encode("utf-8")


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _safe_metadata(
    *, raw_type: str, event_type: NormalizedResendEventType, data: Mapping[str, Any]
) -> dict[str, str]:
    metadata = {"source_type": raw_type}
    if event_type == "bounced":
        raw_bounce = data.get("bounce")
        if isinstance(raw_bounce, Mapping):
            bounce_type = _safe_str(raw_bounce.get("type"))
            bounce_subtype = _safe_str(raw_bounce.get("subType"))
            if bounce_type is not None:
                metadata["bounce_type"] = bounce_type
            if bounce_subtype is not None:
                metadata["bounce_subtype"] = bounce_subtype
    return metadata
