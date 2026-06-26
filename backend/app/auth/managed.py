"""Managed (production) Clerk AuthService factory.

Constructs ``AuthService`` with a shared ``ClerkJwksVerifier`` singleton
(stored on ``app.state.clerk_verifier`` at startup so the JWKS cache persists
across requests) and request-scoped DB-backed repositories opened under
``auth_context_session``.

Used only by ``app.auth.dependencies.auth_service``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth.clerk_jwks import ClerkJwksVerifier
from app.repositories.auth_session_repo import AuthSessionRepository
from app.repositories.membership_repo import MembershipRepository
from app.repositories.user_repo import UserRepository
from app.services.auth import AuthService

# Mirrors _PLACEHOLDER_MARKERS in boot_guard — kept in sync; both guard against
# unconfigured settings reaching production code paths.
_PLACEHOLDER_MARKERS = ("change_me", "changeme", "placeholder", "todo", "xxx")


def is_managed_auth_configured(settings: Any) -> bool:
    """True when managed-auth issuer is present and not a placeholder value."""
    issuer = settings.auth_provider_issuer
    if not issuer or len(issuer.strip()) < 8:
        return False
    lower = issuer.lower()
    return not any(m in lower for m in _PLACEHOLDER_MARKERS)


def make_managed_auth_service(
    verifier: ClerkJwksVerifier,
    conn: AsyncConnection,
) -> AuthService:
    """Build an ``AuthService`` for the managed Clerk auth path.

    The verifier is shared (singleton); the repositories are request-scoped
    and must be called from within an ``auth_context_session`` transaction.
    """
    return AuthService(
        verifier=verifier,
        users=UserRepository(conn),
        memberships=MembershipRepository(conn),
        sessions=AuthSessionRepository(conn),
    )
