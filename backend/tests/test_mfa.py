"""MFA enforcement policy tests (P3-3b).

Exercises the enforcement mechanism against the *available* role path without
inventing a platform_admin role in the RBAC matrix. The default config names
platform_admin (owner decision), but the helper is generic over any role set.
"""

import uuid

import pytest

from app.auth.mfa import enforce_mfa, mfa_required_roles
from app.auth.principal import CurrentPrincipal
from app.config import Settings
from app.middleware.error_handler import AppError


def _principal(*, role: str, mfa_verified: bool) -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_1",
        provider_session_ref="sess_1",
        user_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        email="owner@example.com",
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        role=role,
        membership_version=1,
        mfa_verified=mfa_verified,
    )


def test_default_required_roles_includes_platform_admin() -> None:
    assert mfa_required_roles(Settings()) == frozenset({"platform_admin"})


def test_required_roles_parses_comma_list() -> None:
    settings = Settings(auth_mfa_required_roles="platform_admin, owner ,")
    assert mfa_required_roles(settings) == frozenset({"platform_admin", "owner"})


def test_required_role_without_mfa_is_blocked() -> None:
    with pytest.raises(AppError) as exc:
        enforce_mfa(
            _principal(role="admin", mfa_verified=False), required_roles=frozenset({"admin"})
        )
    assert exc.value.code == "MFA_REQUIRED"
    assert exc.value.status_code == 403


def test_required_role_with_mfa_passes() -> None:
    enforce_mfa(_principal(role="admin", mfa_verified=True), required_roles=frozenset({"admin"}))


def test_unlisted_role_never_requires_mfa() -> None:
    # Tenant owner/admin are not weakened: outside the required set, MFA is not forced.
    enforce_mfa(
        _principal(role="owner", mfa_verified=False), required_roles=frozenset({"platform_admin"})
    )


def test_empty_required_set_is_noop() -> None:
    enforce_mfa(_principal(role="platform_admin", mfa_verified=False), required_roles=frozenset())
