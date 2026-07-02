"""Tests for the local/mock-only demo tenant bootstrap (P4-FreshVolumeBootstrap)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.auth.local_mock import _PROVIDER_USER_ID, _LocalMockUsers
from app.config import Settings
from app.scripts.bootstrap_local_demo import (
    _USER_IDENTITY_PROVIDER,
    _USER_PROVIDER_USER_ID,
    DEFAULT_TENANT_ID,
    DEFAULT_USER_ID,
    BootstrapEnvironmentError,
    bootstrap_local_demo,
    ensure_bootstrap_env_allowed,
)

_TENANT = uuid.UUID("33333333-3333-3333-3333-333333333333")
_USER = uuid.UUID("44444444-4444-4444-4444-444444444444")


def test_bootstrap_refuses_non_local_envs() -> None:
    for env in ("staging", "production", "some-unknown-env"):
        with pytest.raises(BootstrapEnvironmentError):
            ensure_bootstrap_env_allowed(Settings(app_env=env))


def test_bootstrap_allows_local_mock_envs() -> None:
    for env in ("local", "development", "demo"):
        ensure_bootstrap_env_allowed(Settings(app_env=env))


@dataclass
class _FakeTenant:
    id: uuid.UUID
    name: str


class _FakeTenantRepo:
    def __init__(self, tenant: _FakeTenant | None = None) -> None:
        self.tenant = tenant
        self.create_calls = 0
        self.get_calls: list[uuid.UUID] = []

    async def get_current_tenant(self, *, tenant_id: uuid.UUID) -> _FakeTenant | None:
        self.get_calls.append(tenant_id)
        if self.tenant is not None and self.tenant.id != tenant_id:
            return None
        return self.tenant

    async def create(self, *, id: uuid.UUID, name: str) -> _FakeTenant:
        self.create_calls += 1
        self.tenant = _FakeTenant(id=id, name=name)
        return self.tenant


@dataclass
class _FakeUser:
    id: uuid.UUID
    email: str
    identity_provider: str
    provider_user_id: str


class _FakeUserRepo:
    def __init__(self, user: _FakeUser | None = None) -> None:
        self.user = user
        self.create_calls = 0

    async def get_by_identity(
        self, *, identity_provider: str, provider_user_id: str
    ) -> _FakeUser | None:
        if (
            self.user is not None
            and self.user.identity_provider == identity_provider
            and self.user.provider_user_id == provider_user_id
        ):
            return self.user
        return None

    async def create(
        self, *, id: uuid.UUID, email: str, identity_provider: str, provider_user_id: str
    ) -> _FakeUser:
        self.create_calls += 1
        self.user = _FakeUser(
            id=id,
            email=email,
            identity_provider=identity_provider,
            provider_user_id=provider_user_id,
        )
        return self.user


@dataclass
class _FakeMembership:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str


class _FakeMembershipRepo:
    def __init__(self, membership: _FakeMembership | None = None) -> None:
        self.membership = membership
        self.create_calls = 0

    async def get_for_user_and_tenant(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> _FakeMembership | None:
        if (
            self.membership is not None
            and self.membership.user_id == user_id
            and self.membership.tenant_id == tenant_id
        ):
            return self.membership
        return None

    async def create(
        self, *, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> _FakeMembership:
        self.create_calls += 1
        self.membership = _FakeMembership(tenant_id=tenant_id, user_id=user_id, role=role)
        return self.membership


@dataclass
class _FakePlan:
    id: uuid.UUID
    key: str
    name: str
    features: dict[str, Any]


@dataclass
class _FakeSubscription:
    tenant_id: uuid.UUID
    plan_id: uuid.UUID
    tenant_status: str


class _FakeBillingRepo:
    def __init__(
        self, plan: _FakePlan | None = None, subscription: _FakeSubscription | None = None
    ) -> None:
        self.plan = plan
        self.subscription = subscription
        self.plan_create_calls = 0
        self.subscription_create_calls = 0

    async def get_plan_by_key(self, key: str) -> _FakePlan | None:
        return self.plan if self.plan is not None and self.plan.key == key else None

    async def create_plan(self, *, key: str, name: str, features: dict[str, Any]) -> _FakePlan:
        self.plan_create_calls += 1
        self.plan = _FakePlan(id=uuid.uuid4(), key=key, name=name, features=features)
        return self.plan

    async def get_subscription(self, tenant_id: uuid.UUID) -> _FakeSubscription | None:
        if self.subscription is not None and self.subscription.tenant_id == tenant_id:
            return self.subscription
        return None

    async def create_subscription(
        self, *, tenant_id: uuid.UUID, plan_id: uuid.UUID, tenant_status: str
    ) -> _FakeSubscription:
        self.subscription_create_calls += 1
        self.subscription = _FakeSubscription(
            tenant_id=tenant_id, plan_id=plan_id, tenant_status=tenant_status
        )
        return self.subscription


@dataclass
class _FakeComplianceProfile:
    tenant_id: uuid.UUID
    jurisdiction: str
    sending_review_required: bool
    live_sending_allowed: bool
    sms_allowed: bool


class _FakeComplianceRepo:
    def __init__(self) -> None:
        self.upsert_calls = 0
        self.profile: _FakeComplianceProfile | None = None

    async def upsert_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        jurisdiction: str,
        sending_review_required: bool,
        live_sending_allowed: bool,
        sms_allowed: bool,
    ) -> _FakeComplianceProfile:
        self.upsert_calls += 1
        self.profile = _FakeComplianceProfile(
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            sending_review_required=sending_review_required,
            live_sending_allowed=live_sending_allowed,
            sms_allowed=sms_allowed,
        )
        return self.profile


@dataclass
class _Fakes:
    tenant_repo: _FakeTenantRepo = field(default_factory=_FakeTenantRepo)
    user_repo: _FakeUserRepo = field(default_factory=_FakeUserRepo)
    membership_repo: _FakeMembershipRepo = field(default_factory=_FakeMembershipRepo)
    billing_repo: _FakeBillingRepo = field(default_factory=_FakeBillingRepo)
    compliance_repo: _FakeComplianceRepo = field(default_factory=_FakeComplianceRepo)


async def _run_bootstrap(fakes: _Fakes) -> Any:
    return await bootstrap_local_demo(
        tenant_repo=fakes.tenant_repo,  # type: ignore[arg-type]
        user_repo=fakes.user_repo,  # type: ignore[arg-type]
        membership_repo=fakes.membership_repo,  # type: ignore[arg-type]
        billing_repo=fakes.billing_repo,  # type: ignore[arg-type]
        compliance_repo=fakes.compliance_repo,  # type: ignore[arg-type]
        tenant_id=_TENANT,
        user_id=_USER,
    )


@pytest.mark.asyncio
async def test_bootstrap_creates_all_entities_on_first_run() -> None:
    fakes = _Fakes()
    result = await _run_bootstrap(fakes)

    assert result.tenant_created is True
    assert result.user_created is True
    assert result.membership_created is True
    assert result.plan_created is True
    assert result.subscription_created is True

    assert fakes.membership_repo.membership is not None
    assert fakes.membership_repo.membership.role == "owner"

    assert fakes.billing_repo.plan is not None
    assert fakes.billing_repo.plan.key == "mvp_mock"
    assert fakes.billing_repo.subscription is not None
    assert fakes.billing_repo.subscription.tenant_status == "active"

    assert fakes.compliance_repo.profile is not None
    assert fakes.compliance_repo.profile.live_sending_allowed is False
    assert fakes.compliance_repo.profile.sms_allowed is False


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent() -> None:
    fakes = _Fakes()
    first = await _run_bootstrap(fakes)
    assert first.tenant_created is True

    second = await _run_bootstrap(fakes)
    assert second.tenant_created is False
    assert second.user_created is False
    assert second.membership_created is False
    assert second.plan_created is False
    assert second.subscription_created is False

    assert fakes.tenant_repo.create_calls == 1
    assert fakes.user_repo.create_calls == 1
    assert fakes.membership_repo.create_calls == 1
    assert fakes.billing_repo.plan_create_calls == 1
    assert fakes.billing_repo.subscription_create_calls == 1
    # Compliance upsert always runs (already idempotent) — twice is expected.
    assert fakes.compliance_repo.upsert_calls == 2


@pytest.mark.asyncio
async def test_bootstrap_partial_state_is_completed_not_duplicated() -> None:
    existing_tenant = _FakeTenant(id=_TENANT, name="Pre-existing Tenant")
    existing_user = _FakeUser(
        id=_USER,
        email="owner@example.com",
        identity_provider="clerk",
        provider_user_id="local_mock_user",
    )
    fakes = _Fakes(
        tenant_repo=_FakeTenantRepo(tenant=existing_tenant),
        user_repo=_FakeUserRepo(user=existing_user),
    )

    result = await _run_bootstrap(fakes)

    assert result.tenant_created is False
    assert result.user_created is False
    assert result.membership_created is True
    assert result.plan_created is True
    assert result.subscription_created is True
    assert fakes.tenant_repo.create_calls == 0
    assert fakes.user_repo.create_calls == 0


def test_bootstrap_default_identity_matches_mock_auth() -> None:
    # DEFAULT_TENANT_ID/DEFAULT_USER_ID must stay in sync with app/auth/local_mock.py
    # and seed_local_grounding.py so the mock-auth verifier keeps working unchanged.
    assert str(DEFAULT_TENANT_ID) == "22222222-2222-2222-2222-222222222222"
    assert str(DEFAULT_USER_ID) == "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_bootstrap_user_identity_matches_local_mock_auth_users() -> None:
    # The `users` row this script provisions must resolve through
    # app.auth.local_mock._LocalMockUsers.get_by_identity the same way a real
    # Clerk-backed row would, so any code path querying the real table directly
    # (not through the in-memory mock) finds the same identity. A mismatch here
    # previously made the bootstrap's own idempotency check blind to a
    # pre-existing row, causing a duplicate-key crash on re-run.
    assert _USER_PROVIDER_USER_ID == _PROVIDER_USER_ID
    resolved = await _LocalMockUsers().get_by_identity(
        identity_provider=_USER_IDENTITY_PROVIDER, provider_user_id=_USER_PROVIDER_USER_ID
    )
    assert resolved is not None
    assert resolved.id == DEFAULT_USER_ID
