"""MFA enforcement policy (owner decision: platform_admin MFA mandatory at launch).

This module provides a reusable, fail-closed enforcement primitive. It is NOT
attached to ``current_principal`` because ``platform_admin`` is not yet present
in the RBAC role matrix (``services/authz.py`` defines 7 roles, none of which is
``platform_admin``). Per the P3-3b constraint "do not invent a new role model",
enforcement stays inert until that role is added; the mechanism and its tests are
in place so wiring is a one-line change at that point.

See docs/evidence/phase-3-3b-clerk-verifier-implementation.md.
"""

from __future__ import annotations

from app.auth.principal import CurrentPrincipal
from app.config import Settings
from app.middleware.error_handler import AppError


def mfa_required_roles(settings: Settings) -> frozenset[str]:
    """Roles that must present a verified MFA factor, from settings (comma-list)."""
    return frozenset(
        role.strip() for role in settings.auth_mfa_required_roles.split(",") if role.strip()
    )


def enforce_mfa(principal: CurrentPrincipal, *, required_roles: frozenset[str]) -> None:
    """Raise 403 ``MFA_REQUIRED`` when the principal's role demands MFA but lacks it.

    A no-op for roles outside ``required_roles`` (e.g. tenant owner/admin), so it
    never weakens existing tenant access.
    """
    if principal.role in required_roles and not principal.mfa_verified:
        raise AppError(
            "MFA_REQUIRED",
            "Multi-factor authentication is required for this role.",
            status_code=403,
        )
