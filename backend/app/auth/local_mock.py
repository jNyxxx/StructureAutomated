"""Safe local/mock auth wiring for localhost E2E and demos.

This module is intentionally deterministic and must only be attached by the app
entrypoint in non-production environments while mock_verifier is enabled.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from app.auth.verifier import TokenVerificationError, VerifiedClerkClaims
from app.services.auth import AuthMembership, AuthService, AuthUser

_LOCAL_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PRIMARY_TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_TEST_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROVIDER_USER_ID = "local_mock_user"
_PROVIDER_SESSION_REF_PREFIX = "local_mock_session_ref"
_LOCAL_STATIC_TOKENS = (
    "token-sentinel",
    "fake-valid-token",
)  # noqa: S105 - fake local/mock tokens only
_LOCAL_DEMO_TOKEN_PREFIX = f"{_LOCAL_STATIC_TOKENS[0]}:"
_LOCAL_DEMO_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def _claims_for_session_ref(provider_session_ref: str) -> VerifiedClerkClaims:
    return VerifiedClerkClaims(
        provider_user_id=_PROVIDER_USER_ID,
        email="owner@example.com",
        provider_session_ref=provider_session_ref,
        expires_at=1_893_456_000,
        mfa_verified=True,
    )


class LocalDemoMockClerkVerifier:
    """Verifier for local demo tokens with per-login session refs.

    Static tokens remain available for existing CLI/curl smoke tests. The browser
    demo uses ``token-sentinel:<session-id>`` so logout can revoke only the
    current local mock session while a fresh demo login receives a fresh session
    reference. This class is wired only by ``build_local_mock_auth_service()`` in
    non-production mock mode.
    """

    async def verify(self, token: str) -> VerifiedClerkClaims:
        if token in _LOCAL_STATIC_TOKENS:
            return _claims_for_session_ref(f"{_PROVIDER_SESSION_REF_PREFIX}:{token}")

        if token.startswith(_LOCAL_DEMO_TOKEN_PREFIX):
            session_id = token.removeprefix(_LOCAL_DEMO_TOKEN_PREFIX)
            if _LOCAL_DEMO_SESSION_ID_RE.fullmatch(session_id):
                return _claims_for_session_ref(f"{_PROVIDER_SESSION_REF_PREFIX}:{session_id}")

        raise TokenVerificationError("invalid token")


class _LocalMockUsers:
    async def get_by_identity(
        self, *, identity_provider: str, provider_user_id: str
    ) -> AuthUser | None:
        if identity_provider != "clerk" or provider_user_id != _PROVIDER_USER_ID:
            return None
        return AuthUser(
            id=_LOCAL_USER_ID,
            email="owner@example.com",
            identity_provider="clerk",
            provider_user_id=_PROVIDER_USER_ID,
        )


class _LocalMockMemberships:
    async def get_for_user_and_tenant(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> AuthMembership | None:
        if user_id != _LOCAL_USER_ID or tenant_id not in {_PRIMARY_TENANT_ID, _TEST_TENANT_ID}:
            return None
        return AuthMembership(
            tenant_id=tenant_id,
            user_id=user_id,
            role="owner",
            membership_version=1,
            tenant_status="active",
        )


class _LocalMockSessions:
    def __init__(self) -> None:
        self._revoked: set[str] = set()

    async def is_revoked(self, provider_session_ref: str) -> bool:
        return provider_session_ref in self._revoked

    async def upsert_active(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        provider_session_ref: str,
        membership_version: int,
        expires_at: datetime | None,
    ) -> None:
        return None

    async def revoke(self, *, provider_session_ref: str, revoked_at: datetime) -> int:
        self._revoked.add(provider_session_ref)
        return 1

    async def revoke_all_for_user(self, *, user_id: uuid.UUID, revoked_at: datetime) -> int:
        self._revoked.update(
            f"{_PROVIDER_SESSION_REF_PREFIX}:{token}" for token in _LOCAL_STATIC_TOKENS
        )
        return 1


def build_local_mock_auth_service() -> AuthService:
    """Build an in-memory AuthService for non-production local/mock E2E only."""
    return AuthService(
        verifier=LocalDemoMockClerkVerifier(),
        users=_LocalMockUsers(),
        memberships=_LocalMockMemberships(),
        sessions=_LocalMockSessions(),
    )
