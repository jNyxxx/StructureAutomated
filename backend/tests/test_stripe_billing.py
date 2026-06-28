"""Stripe checkout / billing portal skeleton tests for P3-6e."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime

import pytest

from app.auth.principal import CurrentPrincipal
from app.config import Settings
from app.middleware.error_handler import AppError
from app.services.authz import RBACService
from app.services.billing import BillingGateService, BillingPlan, TenantSubscriptionRecord
from app.services.stripe_billing import (
    DisabledStripeBillingProvider,
    StripeBillingAPIService,
    StripeBillingPortalSessionRequest,
    StripeCheckoutSessionRequest,
    build_stripe_billing_provider,
    stripe_billing_config_failures,
    stripe_billing_readiness_summary,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_PLAN_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_NOW = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)


def _principal(role: str = "owner") -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=_USER,
        email="owner@example.com",
        tenant_id=_TENANT,
        role=role,
        membership_version=1,
        mfa_verified=True,
    )


class _BillingStore:
    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord:
        assert tenant_id == _TENANT
        return TenantSubscriptionRecord(
            tenant_id=_TENANT,
            plan=BillingPlan(
                id=_PLAN_ID,
                key="mock_growth",
                name="Mock Growth",
                features={
                    "can_send": True,
                    "can_run_agents": True,
                    "can_create_campaign": True,
                    "can_export": True,
                },
            ),
            tenant_status="active",
            grace_until=None,
        )

    async def set_status(self, **kwargs: object) -> TenantSubscriptionRecord:
        raise AssertionError("Stripe skeleton must not mutate billing state")


def _service(settings: Settings) -> StripeBillingAPIService:
    return StripeBillingAPIService(
        billing=BillingGateService(_BillingStore()),
        rbac=RBACService(),
        provider=build_stripe_billing_provider(settings),
    )


def test_mock_billing_remains_default_and_checkout_portal_disabled() -> None:
    settings = Settings()
    summary = stripe_billing_readiness_summary(settings)

    assert settings.mock_stripe is True
    assert settings.stripe_mode == "test"
    assert settings.stripe_checkout_enabled is False
    assert settings.stripe_billing_portal_enabled is False
    assert summary == {
        "checkout_enabled": False,
        "portal_enabled": False,
        "config_ready": False,
        "test_mode": True,
        "mock_stripe": True,
    }


async def test_checkout_disabled_by_default_fails_closed() -> None:
    provider = DisabledStripeBillingProvider(
        checkout_enabled=False,
        portal_enabled=False,
        config_failures=(),
    )

    with pytest.raises(AppError) as excinfo:
        await provider.create_checkout_session(
            StripeCheckoutSessionRequest(tenant_id=_TENANT, actor_user_id=_USER)
        )

    assert excinfo.value.code == "STRIPE_CHECKOUT_NOT_AVAILABLE"
    assert excinfo.value.status_code == 503


async def test_portal_disabled_by_default_fails_closed() -> None:
    provider = DisabledStripeBillingProvider(
        checkout_enabled=False,
        portal_enabled=False,
        config_failures=(),
    )

    with pytest.raises(AppError) as excinfo:
        await provider.create_billing_portal_session(
            StripeBillingPortalSessionRequest(tenant_id=_TENANT, actor_user_id=_USER)
        )

    assert excinfo.value.code == "STRIPE_PORTAL_NOT_AVAILABLE"
    assert excinfo.value.status_code == 503


async def test_incomplete_config_fails_closed_when_checkout_enabled() -> None:
    settings = Settings(stripe_checkout_enabled=True)

    with pytest.raises(AppError) as excinfo:
        await _service(settings).create_checkout_session(_principal(), now=_NOW)

    assert excinfo.value.code == "STRIPE_CONFIG_NOT_READY"
    assert excinfo.value.details == {}


async def test_complete_test_config_still_does_not_create_checkout_session() -> None:
    settings = Settings(
        stripe_checkout_enabled=True,
        stripe_secret_key_ref="ref_billing_test_server",
        stripe_success_url="https://staging.automatedstructure.com/billing/success",
        stripe_cancel_url="https://staging.automatedstructure.com/billing/cancel",
        stripe_price_ids_ref="ref_billing_test_prices",
    )

    with pytest.raises(AppError) as excinfo:
        await _service(settings).create_checkout_session(_principal(), now=_NOW)

    assert stripe_billing_config_failures(settings) == []
    assert excinfo.value.code == "STRIPE_BILLING_DISABLED"


async def test_complete_test_config_still_does_not_create_billing_portal_session() -> None:
    settings = Settings(
        stripe_billing_portal_enabled=True,
        stripe_secret_key_ref="ref_billing_test_server",
        stripe_portal_return_url="https://staging.automatedstructure.com/billing",
    )

    with pytest.raises(AppError) as excinfo:
        await _service(settings).create_billing_portal_session(_principal(), now=_NOW)

    assert stripe_billing_config_failures(settings) == []
    assert excinfo.value.code == "STRIPE_BILLING_DISABLED"


async def test_stripe_billing_service_requires_billing_permission() -> None:
    settings = Settings(stripe_checkout_enabled=False)

    with pytest.raises(AppError) as excinfo:
        await _service(settings).create_checkout_session(_principal("viewer"), now=_NOW)

    assert excinfo.value.code == "FORBIDDEN"


def test_live_mode_fails_config_readiness_without_live_approval() -> None:
    settings = Settings(stripe_mode="live", stripe_secret_key_ref="ref_billing_live_server")

    failures = stripe_billing_config_failures(settings)

    assert "STRIPE_MODE=live requires separate live billing approval" in failures


def test_stripe_billing_source_has_no_sdk_api_network_or_mutation_markers() -> None:
    from app.services import stripe_billing

    source = inspect.getsource(stripe_billing).lower()
    forbidden = (
        "import " + "stripe",
        "from " + "stripe",
        "api." + "stripe",
        "checkout.sessions" + ".create",
        "billing_portal.sessions" + ".create",
        "requests" + ".",
        "httpx" + ".",
        "update_subscription",
        "transition_subscription",
    )
    for marker in forbidden:
        assert marker not in source
