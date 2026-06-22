"""Auth service: Clerk claims -> app user -> selected tenant membership -> principal.

Clerk owns credentials/login/sessions. The app verifies tokens through an
abstraction, maps provider identity to the internal user row, checks selected
tenant membership, and stores only app-side revocation metadata.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.auth.principal import CurrentPrincipal
from app.auth.verifier import ClerkTokenVerifier, TokenVerificationError, VerifiedClerkClaims
from app.middleware.error_handler import AppError


@dataclass(frozen=True)
class AuthUser:
    id: uuid.UUID
    email: str
    identity_provider: str
    provider_user_id: str
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class AuthMembership:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    membership_version: int = 1
    tenant_status: str = "active"


class AuthUserStore(Protocol):
    async def get_by_identity(
        self, *, identity_provider: str, provider_user_id: str
    ) -> AuthUser | None:
        """Return the internal user mapped to a provider identity."""


class AuthMembershipStore(Protocol):
    async def get_for_user_and_tenant(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> AuthMembership | None:
        """Return membership for the selected tenant, if active and visible."""


class AuthSessionStore(Protocol):
    async def is_revoked(self, provider_session_ref: str) -> bool:
        """Return True when the provider session has been app-side revoked."""

    async def upsert_active(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        provider_session_ref: str,
        membership_version: int,
        expires_at: datetime | None,
    ) -> None:
        """Record the current app-side session metadata."""

    async def revoke(self, *, provider_session_ref: str, revoked_at: datetime) -> int:
        """Revoke one provider session reference."""

    async def revoke_all_for_user(self, *, user_id: uuid.UUID, revoked_at: datetime) -> int:
        """Revoke all app-side sessions for a user."""


AuditRecorder = Callable[..., Awaitable[None]]


def _claims_expiry(claims: VerifiedClerkClaims) -> datetime | None:
    if claims.expires_at is None:
        return None
    return datetime.fromtimestamp(claims.expires_at, tz=UTC)


class AuthService:
    def __init__(
        self,
        *,
        verifier: ClerkTokenVerifier,
        users: AuthUserStore,
        memberships: AuthMembershipStore,
        sessions: AuthSessionStore,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._verifier = verifier
        self._users = users
        self._memberships = memberships
        self._sessions = sessions
        self._audit_record = audit_record

    async def resolve_principal(self, *, token: str, tenant_id: uuid.UUID) -> CurrentPrincipal:
        try:
            claims = await self._verifier.verify(token)
        except TokenVerificationError as exc:
            raise AppError("UNAUTHENTICATED", "Authentication required.", status_code=401) from exc

        if await self._sessions.is_revoked(claims.provider_session_ref):
            raise AppError("AUTH_SESSION_REVOKED", "Authentication required.", status_code=401)

        user = await self._users.get_by_identity(
            identity_provider="clerk", provider_user_id=claims.provider_user_id
        )
        if user is None or user.deleted_at is not None:
            raise AppError("UNAUTHENTICATED", "Authentication required.", status_code=401)

        membership = await self._memberships.get_for_user_and_tenant(
            user_id=user.id, tenant_id=tenant_id
        )
        if membership is None or membership.tenant_status != "active":
            raise AppError("TENANT_ACCESS_DENIED", "No access to selected tenant.", status_code=403)

        await self._sessions.upsert_active(
            user_id=user.id,
            tenant_id=tenant_id,
            provider_session_ref=claims.provider_session_ref,
            membership_version=membership.membership_version,
            expires_at=_claims_expiry(claims),
        )
        return CurrentPrincipal(
            provider_user_id=claims.provider_user_id,
            provider_session_ref=claims.provider_session_ref,
            user_id=user.id,
            email=user.email,
            tenant_id=tenant_id,
            role=membership.role,
            membership_version=membership.membership_version,
            mfa_verified=claims.mfa_verified,
        )

    async def revoke_session(self, principal: CurrentPrincipal, *, now: datetime) -> int:
        count = await self._sessions.revoke(
            provider_session_ref=principal.provider_session_ref, revoked_at=now
        )
        if self._audit_record is not None:
            await self._audit_record(
                event_type="auth.session_revoked",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                details={"provider": "clerk", "session_ref": "redacted"},
            )
        return count

    async def revoke_all_sessions(self, principal: CurrentPrincipal, *, now: datetime) -> int:
        count = await self._sessions.revoke_all_for_user(user_id=principal.user_id, revoked_at=now)
        if self._audit_record is not None:
            await self._audit_record(
                event_type="auth.sessions_revoked_all",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                details={"provider": "clerk", "count": count},
            )
        return count
