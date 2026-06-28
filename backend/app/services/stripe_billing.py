"""Stripe checkout and billing portal skeleton.

P3-6e defines a provider boundary for future test-mode checkout and billing
portal sessions. The implementation in this slice is disabled/fail-closed and
uses no Stripe package, provider API, raw credential resolution, checkout
session creation, billing portal session creation, tenant billing-state mutation,
or money movement.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.config import Settings
from app.middleware.error_handler import AppError
from app.services.authz import CAN_MANAGE_BILLING, RBACService
from app.services.billing import BillingGateService

STRIPE_BILLING_PROVIDER = "stripe"
_PLACEHOLDER_MARKERS = ("change_me", "changeme", "placeholder", "todo", "xxx")


@dataclass(frozen=True)
class StripeCheckoutSessionRequest:
    """Safe request shape for a future checkout-session boundary."""

    tenant_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass(frozen=True)
class StripeBillingPortalSessionRequest:
    """Safe request shape for a future billing-portal-session boundary."""

    tenant_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass(frozen=True)
class StripeSessionResult:
    """Safe future result shape. Not returned by the disabled implementation."""

    provider: str
    session_url: str
    mock_only: bool = True


class StripeBillingProvider(Protocol):
    """Boundary for future Stripe checkout and billing portal session creation."""

    async def create_checkout_session(
        self, request: StripeCheckoutSessionRequest
    ) -> StripeSessionResult:
        """Create a future test-mode checkout session."""

    async def create_billing_portal_session(
        self, request: StripeBillingPortalSessionRequest
    ) -> StripeSessionResult:
        """Create a future test-mode billing portal session."""


class StripeBillingAPIService:
    """API service for fail-closed Stripe checkout/portal skeleton routes."""

    def __init__(
        self,
        *,
        billing: BillingGateService,
        rbac: RBACService,
        provider: StripeBillingProvider,
    ) -> None:
        self._billing = billing
        self._rbac = rbac
        self._provider = provider

    async def create_checkout_session(
        self, principal: CurrentPrincipal, *, now: datetime
    ) -> StripeSessionResult:
        self._rbac.require(principal, CAN_MANAGE_BILLING)
        await self._billing.is_active(principal.tenant_id, now=now)
        return await self._provider.create_checkout_session(
            StripeCheckoutSessionRequest(
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
        )

    async def create_billing_portal_session(
        self, principal: CurrentPrincipal, *, now: datetime
    ) -> StripeSessionResult:
        self._rbac.require(principal, CAN_MANAGE_BILLING)
        await self._billing.is_active(principal.tenant_id, now=now)
        return await self._provider.create_billing_portal_session(
            StripeBillingPortalSessionRequest(
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
        )


class DisabledStripeBillingProvider:
    """Fail-closed Stripe billing provider skeleton."""

    def __init__(
        self,
        *,
        checkout_enabled: bool,
        portal_enabled: bool,
        config_failures: tuple[str, ...],
    ) -> None:
        self._checkout_enabled = checkout_enabled
        self._portal_enabled = portal_enabled
        self._config_failures = config_failures

    async def create_checkout_session(
        self, request: StripeCheckoutSessionRequest
    ) -> StripeSessionResult:
        if not self._checkout_enabled:
            raise AppError(
                "STRIPE_CHECKOUT_NOT_AVAILABLE",
                "Stripe checkout is not available.",
                status_code=503,
            )
        if self._config_failures:
            raise AppError(
                "STRIPE_CONFIG_NOT_READY",
                "Stripe billing config is not ready.",
                status_code=503,
            )
        raise AppError(
            "STRIPE_BILLING_DISABLED",
            "Stripe billing is disabled.",
            status_code=503,
        )

    async def create_billing_portal_session(
        self, request: StripeBillingPortalSessionRequest
    ) -> StripeSessionResult:
        if not self._portal_enabled:
            raise AppError(
                "STRIPE_PORTAL_NOT_AVAILABLE",
                "Stripe billing portal is not available.",
                status_code=503,
            )
        if self._config_failures:
            raise AppError(
                "STRIPE_CONFIG_NOT_READY",
                "Stripe billing config is not ready.",
                status_code=503,
            )
        raise AppError(
            "STRIPE_BILLING_DISABLED",
            "Stripe billing is disabled.",
            status_code=503,
        )


def build_stripe_billing_provider(settings: Settings) -> StripeBillingProvider:
    """Build the disabled Stripe billing provider skeleton."""

    return DisabledStripeBillingProvider(
        checkout_enabled=settings.stripe_checkout_enabled,
        portal_enabled=settings.stripe_billing_portal_enabled,
        config_failures=tuple(stripe_billing_config_failures(settings)),
    )


def stripe_billing_config_failures(settings: Settings) -> list[str]:
    """Return safe missing Stripe billing config labels.

    The helper checks refs and URL presence only. It never resolves raw secret
    values and never validates with Stripe.
    """

    failures: list[str] = []
    if settings.stripe_mode not in {"test", "live"}:
        failures.append("STRIPE_MODE must be test or live")
    if settings.stripe_mode == "live":
        failures.append("STRIPE_MODE=live requires separate live billing approval")
    if _is_placeholder(settings.stripe_secret_key_ref):
        failures.append("STRIPE_SECRET_KEY_REF is blank or placeholder")
    if settings.stripe_checkout_enabled:
        if not _is_safe_url(settings.stripe_success_url):
            failures.append("STRIPE_SUCCESS_URL is blank, placeholder, or unsafe")
        if not _is_safe_url(settings.stripe_cancel_url):
            failures.append("STRIPE_CANCEL_URL is blank, placeholder, or unsafe")
        if _is_placeholder(settings.stripe_price_ids_ref):
            failures.append("STRIPE_PRICE_IDS_REF is blank or placeholder")
    if settings.stripe_billing_portal_enabled:
        if not _is_safe_url(settings.stripe_portal_return_url):
            failures.append("STRIPE_PORTAL_RETURN_URL is blank, placeholder, or unsafe")
    return failures


def stripe_billing_readiness_summary(settings: Settings) -> Mapping[str, bool]:
    """Safe boolean readiness summary for tests/docs; no raw values included."""

    failures = stripe_billing_config_failures(settings)
    return {
        "checkout_enabled": settings.stripe_checkout_enabled,
        "portal_enabled": settings.stripe_billing_portal_enabled,
        "config_ready": len(failures) == 0,
        "test_mode": settings.stripe_mode == "test",
        "mock_stripe": settings.mock_stripe,
    }


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    v = value.strip().lower()
    return v == "" or len(v) < 8 or any(marker in v for marker in _PLACEHOLDER_MARKERS)


def _is_safe_url(value: str | None) -> bool:
    if value is None or _is_placeholder(value):
        return False
    url = value.strip().lower()
    return url.startswith("https://") or url.startswith("http://localhost")
