"""Email provider interface and mock/live boundary for P3-5.

This module is intentionally network-free in P3-5f. It defines the shape future
live adapters must implement, registers the safe mock adapter, and adds a
fail-closed Resend skeleton that cannot send until a later approved smoke slice.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final, Literal, Protocol

from app.config import Settings
from app.middleware.error_handler import AppError

MOCK_EMAIL_PROVIDER: Final = "mock"
RESEND_EMAIL_PROVIDER: Final = "resend"
ProviderStatus = Literal["accepted", "deferred", "failed"]
_PROVIDER_STATUS_ACCEPTED: Final[ProviderStatus] = "accepted"
_PROVIDER_STATUS_DEFERRED: Final[ProviderStatus] = "deferred"
_PROVIDER_STATUS_FAILED: Final[ProviderStatus] = "failed"
_REQUIRED_RESEND_CAP_FIELDS: Final = (
    "email_tenant_hourly_cap",
    "email_tenant_daily_cap",
    "email_campaign_daily_cap",
    "email_mailbox_daily_cap",
)


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
    send_layer: Literal["transactional", "cold_outreach"] = "cold_outreach"
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

    def __init__(
        self,
        *,
        code: str = "EMAIL_PROVIDER_NOT_AVAILABLE",
        message: str = "Email provider is not available.",
    ) -> None:
        super().__init__(code, message, status_code=503)


class LiveEmailProviderDisabled(AppError):
    """Raised by live-provider skeletons that are intentionally not deliverable yet."""

    def __init__(self) -> None:
        super().__init__(
            "LIVE_EMAIL_PROVIDER_DISABLED",
            "Live email provider is disabled.",
            status_code=503,
        )


class ColdOutreachNotAllowedOnTransactionalProvider(AppError):
    """Raised when a cold-outreach send intent reaches a transactional-only provider.

    Resend handles transactional/opted-in sends only. Cold outreach must route
    through the dedicated mailbox-pool manager (future, mocked for MVP).
    """

    def __init__(self, provider: str = "resend") -> None:
        super().__init__(
            "COLD_OUTREACH_NOT_ALLOWED",
            f"Provider '{provider}' handles transactional/opted-in sends only. "
            "Cold outreach must use the dedicated mailbox-pool manager.",
            status_code=422,
        )


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


@dataclass
class ResendEmailSendProvider:
    """Fail-closed Resend adapter skeleton.

    P3-5f intentionally does not import a provider SDK, perform outbound calls,
    resolve secret values, or emit raw provider responses. A later owner-approved
    smoke slice must replace this method with a real adapter implementation after
    the DNS, secret-ref, webhook, cap, legal, and internal-recipient gates clear.
    """

    live_enabled: bool
    secret_ref: str | None
    webhook_secret_ref: str | None
    sending_domain: str | None
    webhooks_enabled: bool = False
    kind: str = RESEND_EMAIL_PROVIDER

    async def send(self, message: ProviderSendRequest) -> ProviderSendResult:
        if message.send_layer == "cold_outreach":
            raise ColdOutreachNotAllowedOnTransactionalProvider(self.kind)
        raise LiveEmailProviderDisabled()


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    v = value.strip().lower()
    return (
        v == ""
        or len(v) < 8
        or any(marker in v for marker in ("change_me", "changeme", "placeholder", "todo", "xxx"))
    )


def _is_positive_int(value: int | None) -> bool:
    return isinstance(value, int) and value > 0


def resend_config_failures(settings: Settings) -> list[str]:
    """Return safe Resend config failure labels without exposing secret values."""
    failures: list[str] = []
    if _is_placeholder(settings.email_provider_secret_ref):
        failures.append("EMAIL_PROVIDER_SECRET_REF is blank or placeholder")
    if settings.email_provider_webhooks_enabled and _is_placeholder(
        settings.email_provider_webhook_secret_ref
    ):
        failures.append("EMAIL_PROVIDER_WEBHOOK_SECRET_REF is blank or placeholder")
    if _is_placeholder(settings.email_sending_domain):
        failures.append("EMAIL_SENDING_DOMAIN is blank or placeholder")
    for field_name in _REQUIRED_RESEND_CAP_FIELDS:
        if not _is_positive_int(getattr(settings, field_name)):
            failures.append(f"{field_name.upper()} must be a positive integer")
    return failures


class EmailProviderRegistry:
    """Fail-closed adapter registry.

    Live provider keys must not silently resolve to mock. Resend can resolve only
    to a disabled skeleton in P3-5f; real delivery remains unreachable.
    """

    def __init__(
        self,
        *,
        mock_provider: EmailSendProvider | None = None,
        resend_provider: EmailSendProvider | None = None,
    ) -> None:
        self._mock_provider = mock_provider or MockEmailSendProvider()
        self._resend_provider = resend_provider

    def resolve(
        self,
        *,
        provider_key: str,
        live_enabled: bool,
        settings: Settings | None = None,
    ) -> EmailSendProvider:
        provider = provider_key.strip().lower()
        if provider == MOCK_EMAIL_PROVIDER and not live_enabled:
            return self._mock_provider
        if provider == MOCK_EMAIL_PROVIDER and live_enabled:
            raise EmailProviderConfigurationError(code="LIVE_EMAIL_PROVIDER_NOT_IMPLEMENTED")
        if provider == RESEND_EMAIL_PROVIDER:
            if self._resend_provider is not None:
                return self._resend_provider
            if settings is None:
                raise EmailProviderConfigurationError(code="EMAIL_PROVIDER_CONFIG_INCOMPLETE")
            if live_enabled:
                failures = resend_config_failures(settings)
                if failures:
                    raise EmailProviderConfigurationError(code="EMAIL_PROVIDER_CONFIG_INCOMPLETE")
            return ResendEmailSendProvider(
                live_enabled=live_enabled,
                secret_ref=settings.email_provider_secret_ref,
                webhook_secret_ref=settings.email_provider_webhook_secret_ref,
                sending_domain=settings.email_sending_domain,
                webhooks_enabled=settings.email_provider_webhooks_enabled,
            )
        raise EmailProviderConfigurationError()


def build_email_provider(settings: Settings) -> EmailSendProvider:
    """Build the configured email provider without any live-provider fallback."""
    return EmailProviderRegistry().resolve(
        provider_key=settings.email_provider,
        live_enabled=settings.live_email_sending_enabled,
        settings=settings,
    )
