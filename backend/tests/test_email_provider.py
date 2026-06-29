"""Email provider interface boundary tests for P3-5b."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.middleware.error_handler import AppError
from app.services.email_provider import (
    EmailProviderRegistry,
    MockEmailSendProvider,
    ProviderSendRequest,
    build_email_provider,
)

_NOW = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_DRAFT = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _request() -> ProviderSendRequest:
    return ProviderSendRequest(
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        idempotency_key="safe-key",
        requested_at=_NOW,
        recipient_ref="draft:recipient",
        content_ref="draft:content",
        safe_metadata={"mock_only": "true"},
    )


async def test_mock_adapter_returns_safe_accepted_result() -> None:
    provider = MockEmailSendProvider()

    result = await provider.send(_request())

    assert result.provider == "mock"
    assert result.provider_status == "accepted"
    assert result.provider_message_id == f"mock:{_DRAFT}"
    assert result.accepted_at == _NOW
    assert result.safe_metadata == {"mock_only": "true"}
    serialized = repr(result)
    assert "CHANGE_ME" not in serialized
    assert "sk_live" not in serialized
    assert "prospect@example.com" not in serialized


def test_mock_adapter_source_has_no_network_or_provider_sdk_calls() -> None:
    source = inspect.getsource(MockEmailSendProvider).lower()
    forbidden = (
        "sendgrid",
        "postmark",
        "mailgun",
        "boto3",
        "ses",
        "smtplib",
        "smtp",
        "socket",
        "urlopen",
        "requests",
        "httpx",
    )
    for marker in forbidden:
        assert marker not in source


def test_default_registry_resolves_only_mock_when_live_disabled() -> None:
    provider = EmailProviderRegistry().resolve(provider_key="mock", live_enabled=False)
    assert isinstance(provider, MockEmailSendProvider)


@pytest.mark.parametrize("provider_key", ["sendgrid", "postmark", "ses", "mailgun", "smtp"])
def test_unknown_or_live_provider_names_fail_closed(provider_key: str) -> None:
    with pytest.raises(AppError) as excinfo:
        EmailProviderRegistry().resolve(provider_key=provider_key, live_enabled=False)

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.code == "EMAIL_PROVIDER_NOT_AVAILABLE"
    assert provider_key not in exc.message.lower()


def test_live_enabled_mock_provider_fails_closed() -> None:
    with pytest.raises(AppError) as excinfo:
        EmailProviderRegistry().resolve(provider_key="mock", live_enabled=True)

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.code == "LIVE_EMAIL_PROVIDER_NOT_IMPLEMENTED"


def test_build_email_provider_defaults_to_mock() -> None:
    provider = build_email_provider(Settings())
    assert isinstance(provider, MockEmailSendProvider)


def test_build_email_provider_does_not_fallback_live_provider_to_mock() -> None:
    with pytest.raises(AppError):
        build_email_provider(Settings(email_provider="sendgrid"))


def test_provider_send_request_defaults_send_layer_to_cold_outreach() -> None:
    req = ProviderSendRequest(
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        draft_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        idempotency_key="key",
        requested_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert req.send_layer == "cold_outreach"


async def test_mock_provider_accepts_both_send_layers() -> None:
    provider = MockEmailSendProvider()
    base = {
        "tenant_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "draft_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "idempotency_key": "key",
        "requested_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    for layer in ("transactional", "cold_outreach"):
        req = ProviderSendRequest(**base, send_layer=layer)  # type: ignore[arg-type]
        result = await provider.send(req)
        assert result.provider_status == "accepted"
