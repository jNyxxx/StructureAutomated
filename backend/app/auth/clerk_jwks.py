"""Production Clerk JWT verifier (RS256 via JWKS).

Implements the ``ClerkTokenVerifier`` Protocol using only ``cryptography`` for
RS256 signature verification — no PyJWT / jose dependency. JWKS keys are supplied
by an injectable source so tests stay deterministic and offline (a static
in-memory JWKS); production uses an httpx-backed source with a small TTL cache.

Security posture (fails closed on every failure):
- Only ``alg=RS256`` is accepted — ``none`` and HMAC algs are rejected, so a
  public JWKS key can never be abused as an HMAC secret (alg-confusion).
- Signature, issuer, expiry (with small leeway), audience/azp (when configured),
  and required claims are all validated before any principal is produced.
- The raw token is never logged, stored, or echoed into error messages.
- The verifier NEVER falls back to the local mock verifier.
"""

from __future__ import annotations

import base64
import binascii
import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.auth.verifier import TokenVerificationError, VerifiedClerkClaims

_DEFAULT_LEEWAY_SECONDS = 30
Jwk = Mapping[str, Any]


@runtime_checkable
class JwksSource(Protocol):
    """Supplies the current JWKS key list; ``refresh`` forces a re-fetch."""

    async def get_keys(self) -> Sequence[Jwk]:
        """Return the cached/current JWKS ``keys`` list."""

    async def refresh(self) -> Sequence[Jwk]:
        """Force-refresh and return the JWKS ``keys`` list (used on kid miss)."""


class StaticJwksSource:
    """In-memory JWKS source for tests / fixtures. No network."""

    def __init__(self, keys: Sequence[Jwk]) -> None:
        self._keys = list(keys)

    async def get_keys(self) -> Sequence[Jwk]:
        return self._keys

    async def refresh(self) -> Sequence[Jwk]:
        return self._keys


class HttpxJwksSource:
    """Fetches JWKS over HTTPS with a small in-memory TTL cache.

    httpx is imported lazily so importing this module never requires it. Any
    network/parse error fails closed via ``TokenVerificationError`` — the
    verifier must never fall back to a mock in production.
    """

    def __init__(
        self,
        url: str,
        *,
        ttl_seconds: int = 3600,
        timeout_seconds: float = 5.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._url = url
        self._ttl = ttl_seconds
        self._timeout = timeout_seconds
        self._clock = clock
        self._cache: list[Jwk] | None = None
        self._fetched_at = 0.0

    async def get_keys(self) -> Sequence[Jwk]:
        if self._cache is None or (self._clock() - self._fetched_at) > self._ttl:
            return await self.refresh()
        return self._cache

    async def refresh(self) -> Sequence[Jwk]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(self._url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 - any fetch/parse error fails closed
            raise TokenVerificationError("jwks unavailable") from exc
        keys = data.get("keys") if isinstance(data, Mapping) else None
        if not isinstance(keys, list):
            raise TokenVerificationError("malformed jwks")
        self._cache = keys
        self._fetched_at = self._clock()
        return keys


def _b64url_decode(segment: str) -> bytes:
    padded = segment + "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(padded)
    except (binascii.Error, ValueError) as exc:
        raise TokenVerificationError("malformed token") from exc


def _b64url_to_int(value: str) -> int:
    return int.from_bytes(_b64url_decode(value), "big")


def _find_key(keys: Sequence[Jwk], kid: str) -> Jwk | None:
    for jwk in keys:
        if jwk.get("kid") == kid and jwk.get("kty") == "RSA":
            return jwk
    return None


def _rsa_public_key(jwk: Jwk) -> rsa.RSAPublicKey:
    try:
        modulus = _b64url_to_int(jwk["n"])
        exponent = _b64url_to_int(jwk["e"])
    except (KeyError, TypeError, ValueError, TokenVerificationError) as exc:
        raise TokenVerificationError("malformed jwks") from exc
    return rsa.RSAPublicNumbers(exponent, modulus).public_key()


def _audience_ok(claim: object, expected: str) -> bool:
    if isinstance(claim, str):
        return claim == expected
    if isinstance(claim, list | tuple):
        return expected in claim
    return False


class ClerkJwksVerifier:
    """RS256/JWKS implementation of the ``ClerkTokenVerifier`` Protocol."""

    def __init__(
        self,
        *,
        jwks: JwksSource,
        issuer: str,
        audience: str | None = None,
        authorized_parties: Sequence[str] = (),
        email_claim: str = "email",
        session_claim: str = "sid",
        mfa_claim: str | None = None,
        leeway_seconds: int = _DEFAULT_LEEWAY_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._jwks = jwks
        self._issuer = issuer
        self._audience = audience
        self._authorized_parties = tuple(authorized_parties)
        self._email_claim = email_claim
        self._session_claim = session_claim
        self._mfa_claim = mfa_claim
        self._leeway = leeway_seconds
        self._clock = clock

    async def verify(self, token: str) -> VerifiedClerkClaims:
        header, payload, header_seg, payload_seg, signature = _split(token)

        # Reject alg confusion / 'none'; only RS256 signatures are accepted.
        if header.get("alg") != "RS256":
            raise TokenVerificationError("unsupported alg")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise TokenVerificationError("missing kid")

        public_key = await self._public_key_for_kid(kid)
        signing_input = f"{header_seg}.{payload_seg}".encode("ascii")
        try:
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature as exc:
            raise TokenVerificationError("bad signature") from exc

        if payload.get("iss") != self._issuer:
            raise TokenVerificationError("issuer mismatch")

        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise TokenVerificationError("missing exp")
        if self._clock() > exp + self._leeway:
            raise TokenVerificationError("token expired")

        if self._audience is not None and not _audience_ok(payload.get("aud"), self._audience):
            raise TokenVerificationError("audience mismatch")
        if self._authorized_parties and payload.get("azp") not in self._authorized_parties:
            raise TokenVerificationError("authorized party mismatch")

        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise TokenVerificationError("missing sub")
        email = payload.get(self._email_claim)
        if not isinstance(email, str) or not email:
            raise TokenVerificationError("missing email")
        session_ref = payload.get(self._session_claim)
        if not isinstance(session_ref, str) or not session_ref:
            raise TokenVerificationError("missing session")

        mfa_verified = bool(payload.get(self._mfa_claim)) if self._mfa_claim is not None else False

        return VerifiedClerkClaims(
            provider_user_id=sub,
            email=email,
            provider_session_ref=session_ref,
            expires_at=exp,
            mfa_verified=mfa_verified,
        )

    async def _public_key_for_kid(self, kid: str) -> rsa.RSAPublicKey:
        jwk = _find_key(await self._jwks.get_keys(), kid)
        if jwk is None:
            # Unknown kid may mean a rotated key; refresh once before failing.
            jwk = _find_key(await self._jwks.refresh(), kid)
        if jwk is None:
            raise TokenVerificationError("unknown kid")
        return _rsa_public_key(jwk)


def _split(token: str) -> tuple[dict[str, Any], dict[str, Any], str, str, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenVerificationError("malformed token")
    header_seg, payload_seg, sig_seg = parts
    try:
        header = json.loads(_b64url_decode(header_seg))
        payload = json.loads(_b64url_decode(payload_seg))
    except (ValueError, TypeError) as exc:
        raise TokenVerificationError("malformed token") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise TokenVerificationError("malformed token")
    return header, payload, header_seg, payload_seg, _b64url_decode(sig_seg)


def build_managed_clerk_verifier(settings: Any) -> ClerkJwksVerifier:
    """Construct a production ClerkJwksVerifier from settings.

    Wired into the managed auth service path once request-scoped DB-backed auth
    stores land (P3-3c+). Boot-guard validation of issuer/keys runs separately.
    """
    issuer = settings.auth_provider_issuer
    if not issuer:
        raise ValueError("AUTH_PROVIDER_ISSUER is required for managed auth")
    jwks_url = settings.auth_provider_jwks_url or f"{issuer.rstrip('/')}/.well-known/jwks.json"
    raw_parties = settings.auth_provider_authorized_parties or ""
    parties = tuple(p.strip() for p in raw_parties.split(",") if p.strip())
    return ClerkJwksVerifier(
        jwks=HttpxJwksSource(jwks_url),
        issuer=issuer,
        audience=settings.auth_provider_audience,
        authorized_parties=parties,
        email_claim=settings.auth_provider_email_claim,
        session_claim=settings.auth_provider_session_claim,
        mfa_claim=settings.auth_provider_mfa_claim,
    )
