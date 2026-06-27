"""Email provider interface and mock/live boundary for P3-5.

This module is intentionally provider-neutral and network-free. It defines the
shape future live adapters must implement, while only registering the safe mock
adapter in this slice.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final, Literal, Protocol

from app.config import Settings
from app.middleware.error_handler import AppError

MOCK_EMAIL_PROVIDER = "mock"
ProviderStatus = Literal["accepted", "deferred", "failed"]
_PROVIDER_STATUS_ACCEPTED: Final[ProviderStatus] = "accepted"
_PROVIDER_STATUS_DEFERRED: Final[ProviderStatus] = "deferred"
_PROVIDER_STATUS_FAILED: Final[ProviderStatus] = "failed"


@dataclass(frozen=True)
class ProviderSendRequest:
    """Safe request shape for an email send provider.

    P3-5b deliberately passes identifiers/references only. Raw credentials are
    never part of this object. Future live adapters may resolve approved content
    and recipients behind the send gate, but must not log or expose them.
    """

    tenant_id: uuid.UUID
    draft_id: uuid.UUID
    idempotency_key: str
    requested_at: datetime
    channel: Literal["email"] = "email"
    recipient_ref: str | None = None
    content_ref: str | None = None
    safe_metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderSendResult:
    """Safe provider result shape.

    ``raw_provider_response_ref`` is only a reference to separately controlled
    evidence. Raw provider payloads may contain PII and must not be embedded in
    this DTO, logs, audit events, or client responses.
    """

    provider: str
    provider_message_id: str | None
    provider_status: ProviderStatus
    accepted_at: datetime | None = None
    raw_provider_response_ref: str | None = None
    safe_metadata: Mapping[str, str] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class EmailSendProvider(Protocol):
    """Provider adapter contract for future email delivery implementations."""

    kind: str

    async def send(self, message: ProviderSendRequest) -> ProviderSendResult:
        """Send or simulate an email send after all server-side gates pass."""


class EmailProviderConfigurationError(AppError):
    """Raised when an email provider is not safely available."""

    def __init__(self, *, code: str = "EMAIL_PROVIDER_NOT_AVAILABLE") -> None:
        super().__init__(code, "Email provider is not available.", status_code=503)


class MockEmailSendProvider:
    """Network-free mock adapter used for local/demo send intent behavior."""

    kind = MOCK_EMAIL_PROVIDER

    async def send(self, message: ProviderSendRequest) -> ProviderSendResult:
        mock_message_id = f"mock:{message.draft_id}"
        return ProviderSendResult(
            provider=self.kind,
            provider_message_id=mock_message_id,
            provider_status=_PROVIDER_STATUS_ACCEPTED,
            accepted_at=message.requested_at,
            safe_metadata={"mock_only": "true"},
        )


class EmailProviderRegistry:
    """Fail-closed adapter registry.

    P3-5b intentionally registers only the mock adapter. Live provider keys must
    not silently resolve to mock; they fail closed until a later owner-approved
    slice adds a real adapter and its boot-guard requirements.
    """

    def __init__(self, *, mock_provider: EmailSendProvider | None = None) -> None:
        self._mock_provider = mock_provider or MockEmailSendProvider()

    def resolve(self, *, provider_key: str, live_enabled: bool) -> EmailSendProvider:
        provider = provider_key.strip().lower()
        if provider == MOCK_EMAIL_PROVIDER and not live_enabled:
            return self._mock_provider
        if provider == MOCK_EMAIL_PROVIDER and live_enabled:
            raise EmailProviderConfigurationError(code="LIVE_EMAIL_PROVIDER_NOT_IMPLEMENTED")
        raise EmailProviderConfigurationError()


def build_email_provider(settings: Settings) -> EmailSendProvider:
    """Build the configured email provider without any live-provider fallback."""
    return EmailProviderRegistry().resolve(
        provider_key=settings.email_provider,
        live_enabled=settings.live_email_sending_enabled,
    )
