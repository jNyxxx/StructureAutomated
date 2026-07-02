"""LOCAL/MOCK-ONLY deterministic demo-tenant bootstrap for a fresh Docker volume.

Creates the demo tenant, owner user, membership, mock billing subscription,
and compliance profile that ``seed_local_grounding.py`` and the local mock
auth verifier (``app/auth/local_mock.py``) both assume already exist. Every
write goes through the same tenant-scoped ``tenant_session`` connection and
repository layer the app itself uses — no raw connections, no RLS bypass, no
gate weakened. Compliance defaults keep live sending and SMS off.

Refuses to run unless ``APP_ENV`` is local/development/demo. Never imported by
a request-handling path — invoke as ``python -m app.scripts.bootstrap_local_demo``.
Run this before ``seed_local_grounding.py`` on a fresh volume.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.database import tenant_session
from app.repositories.billing_repo import BillingRepository
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.membership_repo import MembershipRepository
from app.repositories.tenant_repo import TenantRepository
from app.repositories.user_repo import UserRepository

_ALLOWED_BOOTSTRAP_ENVS = frozenset({"local", "development", "demo"})

# Identity constants mirroring app/auth/local_mock.py and seed_local_grounding.py
# so the mock-auth verifier keeps resolving the same tenant/user/token unchanged.
DEFAULT_TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEFAULT_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TENANT_NAME = "Automated Structure Local Mock Tenant"
_USER_EMAIL = "owner@example.com"
_USER_IDENTITY_PROVIDER = "local_mock"
_USER_PROVIDER_USER_ID = "local_mock_user"
_MEMBERSHIP_ROLE = "owner"
_PLAN_KEY = "mvp_mock"
_PLAN_NAME = "MVP Mock Plan"
_PLAN_FEATURES = {"drafts": True, "sending": True, "research": True}
_SUBSCRIPTION_STATUS = "active"
_COMPLIANCE_JURISDICTION = "US"


class BootstrapEnvironmentError(RuntimeError):
    """Raised when the bootstrap is invoked outside an allowed local/mock environment."""


@dataclass(frozen=True)
class BootstrapResult:
    tenant_created: bool
    user_created: bool
    membership_created: bool
    plan_created: bool
    subscription_created: bool
    tenant_id: uuid.UUID
    user_id: uuid.UUID


def ensure_bootstrap_env_allowed(settings: Settings) -> None:
    if settings.app_env not in _ALLOWED_BOOTSTRAP_ENVS:
        raise BootstrapEnvironmentError(
            f"Refusing to bootstrap local demo tenant: APP_ENV={settings.app_env!r} is not one "
            f"of {sorted(_ALLOWED_BOOTSTRAP_ENVS)}. This bootstrap is local/mock/demo-only."
        )


async def bootstrap_local_demo(
    *,
    tenant_repo: TenantRepository,
    user_repo: UserRepository,
    membership_repo: MembershipRepository,
    billing_repo: BillingRepository,
    compliance_repo: ComplianceRepository,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> BootstrapResult:
    """Idempotently provision the demo tenant/user/membership/billing/compliance rows."""
    tenant_created = False
    if await tenant_repo.get_current_tenant() is None:
        await tenant_repo.create(id=tenant_id, name=_TENANT_NAME)
        tenant_created = True

    user_created = False
    existing_user = await user_repo.get_by_identity(
        identity_provider=_USER_IDENTITY_PROVIDER, provider_user_id=_USER_PROVIDER_USER_ID
    )
    if existing_user is None:
        await user_repo.create(
            id=user_id,
            email=_USER_EMAIL,
            identity_provider=_USER_IDENTITY_PROVIDER,
            provider_user_id=_USER_PROVIDER_USER_ID,
        )
        user_created = True

    membership_created = False
    existing_membership = await membership_repo.get_for_user_and_tenant(
        user_id=user_id, tenant_id=tenant_id
    )
    if existing_membership is None:
        await membership_repo.create(tenant_id=tenant_id, user_id=user_id, role=_MEMBERSHIP_ROLE)
        membership_created = True

    plan_created = False
    plan = await billing_repo.get_plan_by_key(_PLAN_KEY)
    if plan is None:
        plan = await billing_repo.create_plan(
            key=_PLAN_KEY, name=_PLAN_NAME, features=_PLAN_FEATURES
        )
        plan_created = True

    subscription_created = False
    if await billing_repo.get_subscription(tenant_id) is None:
        await billing_repo.create_subscription(
            tenant_id=tenant_id, plan_id=plan.id, tenant_status=_SUBSCRIPTION_STATUS
        )
        subscription_created = True

    # Always idempotent (checks get_profile internally) — safe local defaults every run.
    await compliance_repo.upsert_profile(
        tenant_id=tenant_id,
        jurisdiction=_COMPLIANCE_JURISDICTION,
        sending_review_required=True,
        live_sending_allowed=False,
        sms_allowed=False,
    )

    return BootstrapResult(
        tenant_created=tenant_created,
        user_created=user_created,
        membership_created=membership_created,
        plan_created=plan_created,
        subscription_created=subscription_created,
        tenant_id=tenant_id,
        user_id=user_id,
    )


async def run(tenant_id: uuid.UUID = DEFAULT_TENANT_ID) -> BootstrapResult:
    ensure_bootstrap_env_allowed(get_settings())
    async with tenant_session(tenant_id=tenant_id, actor_id=DEFAULT_USER_ID) as conn:
        return await bootstrap_local_demo(
            tenant_repo=TenantRepository(conn),
            user_repo=UserRepository(conn),
            membership_repo=MembershipRepository(conn),
            billing_repo=BillingRepository(conn),
            compliance_repo=ComplianceRepository(conn),
            tenant_id=tenant_id,
            user_id=DEFAULT_USER_ID,
        )


def _line(label: str, created: bool) -> str:
    return f"{label}: {'CREATED' if created else 'SKIPPED (already_exists)'}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant-id",
        type=uuid.UUID,
        default=DEFAULT_TENANT_ID,
        help="Target tenant UUID (default: local demo tenant).",
    )
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(run(tenant_id=args.tenant_id))
    except BootstrapEnvironmentError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(f"BOOTSTRAP tenant_id={result.tenant_id} user_id={result.user_id}")
    print(_line("tenant", result.tenant_created))
    print(_line("user", result.user_created))
    print(_line("membership", result.membership_created))
    print(_line("billing_plan", result.plan_created))
    print(_line("billing_subscription", result.subscription_created))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
