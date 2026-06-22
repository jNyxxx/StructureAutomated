"""Clerk token verifier abstraction.

Production will plug in a Clerk JWT verifier here. Tests and local slices use an
in-memory verifier so no live Clerk network calls or secrets are required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TokenVerificationError(Exception):
    """Raised when a bearer token is missing, invalid, expired, or revoked upstream."""


@dataclass(frozen=True)
class VerifiedClerkClaims:
    provider_user_id: str
    email: str
    provider_session_ref: str
    expires_at: int | None = None
    mfa_verified: bool = False


class ClerkTokenVerifier(Protocol):
    async def verify(self, token: str) -> VerifiedClerkClaims:
        """Verify a Clerk-issued token and return safe, non-secret claims."""


class LocalMockClerkVerifier:
    """Deterministic verifier for tests/local demos; stores fake token strings only."""

    def __init__(self, tokens: dict[str, VerifiedClerkClaims] | None = None) -> None:
        self._tokens = tokens or {}

    async def verify(self, token: str) -> VerifiedClerkClaims:
        claims = self._tokens.get(token)
        if claims is None:
            raise TokenVerificationError("invalid token")
        return claims
