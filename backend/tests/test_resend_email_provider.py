"""Resend adapter skeleton tests for P3-5f."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.middleware.error_handler import AppError
from app.observability.boot_guard import config_failures
from app.services.email_provider import (
    RESEND_EMAIL_PROVIDER,
    EmailProviderRegistry,
    MockEmailSendProvider,
    ProviderSendRequest,
    ResendEmailSendProvider,
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
        safe_metadata={"provider": "resend"},
    )


def _transactional_request() -> ProviderSendRequest:
    return ProviderSendRequest(
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        idempotency_key="safe-key",
        requested_at=_NOW,
        send_layer="transactional",
        recipient_ref="draft:recipient",
        content_ref="draft:content",
        safe_metadata={"provider": "resend"},
    )


def _resend_ready_settings(**override: object) -> Settings:
    base: dict[str, object] = {
        "email_provider": "resend",
        "live_email_sending_enabled": True,
        "email_provider_secret_ref": "secret-ref:email/provider",
        "email_provider_webhook_secret_ref": "secret-ref:email/webhook",
        "email_provider_webhooks_enabled": True,
        "email_sending_domain": "outreach.automatedstructure.com",
        "email_tenant_hourly_cap": 10,
        "email_tenant_daily_cap": 50,
        "email_campaign_daily_cap": 50,
        "email_mailbox_daily_cap": 25,
    }
    base.update(override)
    return Settings(**base)  # type: ignore[arg-type]


def _safe_prod(**override: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "production",
        "mock_stripe": False,
        "mock_mailbox": False,
        "mock_dns": False,
        "mock_verifier": False,
        "mock_research": False,
        "jwt_secret": "prod-jwt-0123456789abcd",
        "encryption_key": "prod-enc-0123456789abcd",
        "webhook_secret": "prod-whk-0123456789abcd",
        "cookie_secure": True,
        "csrf_enabled": True,
        "https_only": True,
        "cors_allow_all": False,
        "secret_backend": "aws",
        "auth_provider": "managed",
        "auth_provider_issuer": "https://clerk.example.com",
        "auth_provider_secret_key": "secret-ref:clerk/backend",
        "auth_provider_publishable_key": "public-ref:clerk/frontend",
        "rate_limit_backend": "redis",
        "rate_limit_redis_url": "rediss://redis.example.internal:6379/0",
    }
    base.update(override)
    return Settings(**base)  # type: ignore[arg-type]


def test_default_provider_remains_mock() -> None:
    provider = build_email_provider(Settings())
    assert isinstance(provider, MockEmailSendProvider)


def test_resend_does_not_silently_fallback_to_mock_when_live_disabled() -> None:
    provider = build_email_provider(Settings(email_provider="resend"))
    assert isinstance(provider, ResendEmailSendProvider)
    assert provider.kind == RESEND_EMAIL_PROVIDER
    assert not isinstance(provider, MockEmailSendProvider)


async def test_resend_skeleton_is_disabled_for_send_attempts_without_live_flag() -> None:
    provider = build_email_provider(Settings(email_provider="resend"))

    with pytest.raises(AppError) as excinfo:
        await provider.send(_transactional_request())

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.code == "LIVE_EMAIL_PROVIDER_DISABLED"
    assert exc.details == {}


@pytest.mark.parametrize(
    "override",
    [
        {"email_provider_secret_ref": None},
        {"email_provider_secret_ref": "CHANGE_ME_PLACEHOLDER"},
        {"email_sending_domain": None},
        {"email_tenant_hourly_cap": None},
        {"email_tenant_daily_cap": 0},
        {"email_campaign_daily_cap": -1},
        {"email_mailbox_daily_cap": None},
    ],
)
def test_resend_live_flag_with_incomplete_config_fails_closed(override: dict[str, object]) -> None:
    with pytest.raises(AppError) as excinfo:
        build_email_provider(_resend_ready_settings(**override))

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.code == "EMAIL_PROVIDER_CONFIG_INCOMPLETE"
    assert exc.details == {}


def test_resend_webhooks_require_webhook_secret_when_enabled() -> None:
    with pytest.raises(AppError) as excinfo:
        build_email_provider(_resend_ready_settings(email_provider_webhook_secret_ref=None))

    assert excinfo.value.code == "EMAIL_PROVIDER_CONFIG_INCOMPLETE"


def test_resend_with_complete_live_config_still_returns_disabled_skeleton() -> None:
    provider = build_email_provider(_resend_ready_settings())
    assert isinstance(provider, ResendEmailSendProvider)


async def test_complete_resend_skeleton_still_cannot_send_or_expose_secret_refs() -> None:
    provider = build_email_provider(_resend_ready_settings())

    with pytest.raises(AppError) as excinfo:
        await provider.send(_transactional_request())

    exc = excinfo.value
    serialized = repr(exc.details) + exc.message
    assert exc.code == "LIVE_EMAIL_PROVIDER_DISABLED"
    assert "secret-ref" not in serialized
    assert "outreach.automatedstructure.com" not in serialized
    assert "recipient" not in serialized


def test_resend_skeleton_source_has_no_network_or_sdk_calls() -> None:
    source = inspect.getsource(ResendEmailSendProvider).lower()
    forbidden = (
        "httpx",
        "requests",
        "urlopen",
        "socket",
        "smtplib",
        "smtp",
        "resend.",
        "api_key",
        "authorization",
    )
    for marker in forbidden:
        assert marker not in source


def test_registry_requires_settings_for_resend_resolution() -> None:
    with pytest.raises(AppError) as excinfo:
        EmailProviderRegistry().resolve(provider_key="resend", live_enabled=True)

    assert excinfo.value.code == "EMAIL_PROVIDER_CONFIG_INCOMPLETE"


def test_production_boot_guard_allows_resend_selected_when_live_disabled() -> None:
    assert config_failures(_safe_prod(email_provider="resend")) == []


def test_production_boot_guard_blocks_unsafe_resend_live_config() -> None:
    failures = config_failures(
        _safe_prod(
            email_provider="resend",
            live_email_sending_enabled=True,
            email_provider_secret_ref=None,
            email_sending_domain=None,
        )
    )
    joined = " ".join(failures)
    assert "EMAIL_PROVIDER_SECRET_REF" in joined
    assert "EMAIL_SENDING_DOMAIN" in joined
    assert "EMAIL_TENANT_HOURLY_CAP" in joined


def test_production_boot_guard_blocks_placeholder_resend_secret_ref() -> None:
    failures = config_failures(
        _safe_prod(
            email_provider="resend",
            live_email_sending_enabled=True,
            email_provider_secret_ref="CHANGE_ME_PLACEHOLDER",
            email_sending_domain="outreach.automatedstructure.com",
            email_tenant_hourly_cap=10,
            email_tenant_daily_cap=50,
            email_campaign_daily_cap=50,
            email_mailbox_daily_cap=25,
        )
    )
    assert any("EMAIL_PROVIDER_SECRET_REF" in failure for failure in failures)


def test_production_boot_guard_requires_webhook_secret_when_resend_webhooks_enabled() -> None:
    failures = config_failures(
        _safe_prod(
            email_provider="resend",
            live_email_sending_enabled=True,
            email_provider_secret_ref="secret-ref:email/provider",
            email_provider_webhooks_enabled=True,
            email_provider_webhook_secret_ref=None,
            email_sending_domain="outreach.automatedstructure.com",
            email_tenant_hourly_cap=10,
            email_tenant_daily_cap=50,
            email_campaign_daily_cap=50,
            email_mailbox_daily_cap=25,
        )
    )
    assert any("EMAIL_PROVIDER_WEBHOOK_SECRET_REF" in failure for failure in failures)


def test_controlled_demo_does_not_bypass_resend_boot_guard() -> None:
    failures = config_failures(
        _safe_prod(
            controlled_demo=True,
            controlled_demo_approved_by="owner:ops p3-5f",
            email_provider="resend",
            live_email_sending_enabled=True,
            email_provider_secret_ref=None,
            email_sending_domain=None,
        )
    )
    joined = " ".join(failures)
    assert "EMAIL_PROVIDER_SECRET_REF" in joined
    assert "EMAIL_SENDING_DOMAIN" in joined


def test_staging_live_resend_uses_same_email_fail_closed_guard() -> None:
    failures = config_failures(
        Settings(app_env="staging", email_provider="resend", live_email_sending_enabled=True)
    )
    assert any("EMAIL_PROVIDER_SECRET_REF" in failure for failure in failures)
    assert any("EMAIL_SENDING_DOMAIN" in failure for failure in failures)


def test_production_boot_guard_blocks_enabled_webhooks_without_secret_ref() -> None:
    failures = config_failures(
        _safe_prod(
            email_provider="resend",
            email_provider_webhooks_enabled=True,
            email_provider_webhook_secret_ref=None,
        )
    )
    assert any("EMAIL_PROVIDER_WEBHOOK_SECRET_REF" in failure for failure in failures)


def test_staging_boot_guard_blocks_enabled_webhooks_without_secret_ref() -> None:
    failures = config_failures(
        Settings(
            app_env="staging",
            email_provider="resend",
            email_provider_webhooks_enabled=True,
            email_provider_webhook_secret_ref=None,
        )
    )
    assert any("EMAIL_PROVIDER_WEBHOOK_SECRET_REF" in failure for failure in failures)


def test_controlled_demo_does_not_bypass_webhook_signing_requirements() -> None:
    failures = config_failures(
        _safe_prod(
            controlled_demo=True,
            controlled_demo_approved_by="owner:ops p3-5g",
            email_provider="resend",
            email_provider_webhooks_enabled=True,
            email_provider_webhook_secret_ref=None,
        )
    )
    assert any("EMAIL_PROVIDER_WEBHOOK_SECRET_REF" in failure for failure in failures)


async def test_resend_rejects_cold_outreach_send_layer() -> None:
    provider = build_email_provider(Settings(email_provider="resend"))

    with pytest.raises(AppError) as excinfo:
        await provider.send(_request())  # _request() defaults to cold_outreach

    exc = excinfo.value
    assert exc.status_code == 422
    assert exc.code == "COLD_OUTREACH_NOT_ALLOWED"


async def test_resend_rejects_cold_outreach_even_when_live_enabled() -> None:
    provider = build_email_provider(_resend_ready_settings())

    with pytest.raises(AppError) as excinfo:
        await provider.send(_request())  # cold_outreach default rejected before live check

    exc = excinfo.value
    assert exc.status_code == 422
    assert exc.code == "COLD_OUTREACH_NOT_ALLOWED"


async def test_resend_cold_outreach_rejection_exposes_no_secrets_or_domain() -> None:
    provider = build_email_provider(_resend_ready_settings())

    with pytest.raises(AppError) as excinfo:
        await provider.send(
            ProviderSendRequest(
                tenant_id=_TENANT,
                draft_id=_DRAFT,
                idempotency_key="key",
                requested_at=_NOW,
                send_layer="cold_outreach",
                safe_metadata={"provider": "resend"},
            )
        )

    exc = excinfo.value
    serialized = repr(exc.details) + exc.message
    assert exc.code == "COLD_OUTREACH_NOT_ALLOWED"
    assert "secret-ref" not in serialized
    assert "outreach.automatedstructure.com" not in serialized
