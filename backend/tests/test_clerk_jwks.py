"""ClerkJwksVerifier tests (P3-3b).

Fully deterministic + offline: an RSA key pair is generated with ``cryptography``
and tokens are signed/verified against an in-memory JWKS. No real Clerk secrets,
no network. A fixed clock makes expiry deterministic.
"""

import base64
import json
from collections.abc import Sequence

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.auth.clerk_jwks import (
    ClerkJwksVerifier,
    Jwk,
    StaticJwksSource,
    build_managed_clerk_verifier,
)
from app.auth.verifier import TokenVerificationError, VerifiedClerkClaims

_NOW = 1_800_000_000
_ISSUER = "https://clerk.example.com"
_KID = "test-kid-1"
_OTHER_KID = "rotated-kid-2"

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _int_b64url(value: int) -> str:
    return _b64url(value.to_bytes((value.bit_length() + 7) // 8, "big"))


def _jwk(key: rsa.RSAPrivateKey, kid: str) -> Jwk:
    nums = key.public_key().public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _int_b64url(nums.n),
        "e": _int_b64url(nums.e),
    }


def _claims(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "iss": _ISSUER,
        "sub": "user_clerk_42",
        "email": "owner@example.com",
        "sid": "sess_clerk_ref",
        "exp": _NOW + 3600,
    }
    base.update(overrides)
    return base


def _sign(
    key: rsa.RSAPrivateKey, *, kid: str, claims: dict[str, object], alg: str = "RS256"
) -> str:
    header = {"alg": alg, "typ": "JWT", "kid": kid}
    header_seg = _b64url(json.dumps(header).encode())
    payload_seg = _b64url(json.dumps(claims).encode())
    signing_input = f"{header_seg}.{payload_seg}".encode("ascii")
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{header_seg}.{payload_seg}.{_b64url(signature)}"


def _verifier(*, keys: Sequence[Jwk] | None = None, **kwargs: object) -> ClerkJwksVerifier:
    source = StaticJwksSource(keys if keys is not None else [_jwk(_KEY, _KID)])
    params: dict[str, object] = {
        "jwks": source,
        "issuer": _ISSUER,
        "mfa_claim": "mfa",
        "clock": lambda: float(_NOW),
    }
    params.update(kwargs)
    return ClerkJwksVerifier(**params)  # type: ignore[arg-type]


async def test_valid_token_maps_claims() -> None:
    token = _sign(_KEY, kid=_KID, claims=_claims(mfa=True))
    result = await _verifier().verify(token)

    assert result == VerifiedClerkClaims(
        provider_user_id="user_clerk_42",
        email="owner@example.com",
        provider_session_ref="sess_clerk_ref",
        expires_at=_NOW + 3600,
        mfa_verified=True,
    )


async def test_mfa_claim_absent_or_false_maps_false() -> None:
    no_flag = await _verifier().verify(_sign(_KEY, kid=_KID, claims=_claims()))
    explicit_false = await _verifier().verify(_sign(_KEY, kid=_KID, claims=_claims(mfa=False)))
    assert no_flag.mfa_verified is False
    assert explicit_false.mfa_verified is False


async def test_invalid_signature_fails() -> None:
    # Signed by a different key than the one published in the JWKS.
    token = _sign(_OTHER_KEY, kid=_KID, claims=_claims())
    with pytest.raises(TokenVerificationError):
        await _verifier().verify(token)


async def test_expired_token_fails() -> None:
    token = _sign(_KEY, kid=_KID, claims=_claims(exp=_NOW - 3600))
    with pytest.raises(TokenVerificationError):
        await _verifier().verify(token)


async def test_expiry_within_leeway_passes() -> None:
    token = _sign(_KEY, kid=_KID, claims=_claims(exp=_NOW - 10))
    result = await _verifier(leeway_seconds=30).verify(token)
    assert result.expires_at == _NOW - 10


async def test_wrong_issuer_fails() -> None:
    token = _sign(_KEY, kid=_KID, claims=_claims(iss="https://evil.example.com"))
    with pytest.raises(TokenVerificationError):
        await _verifier().verify(token)


async def test_audience_enforced_when_configured() -> None:
    bad = _sign(_KEY, kid=_KID, claims=_claims(aud="other-aud"))
    with pytest.raises(TokenVerificationError):
        await _verifier(audience="my-aud").verify(bad)

    ok_str = _sign(_KEY, kid=_KID, claims=_claims(aud="my-aud"))
    ok_list = _sign(_KEY, kid=_KID, claims=_claims(aud=["x", "my-aud"]))
    assert (await _verifier(audience="my-aud").verify(ok_str)).provider_user_id == "user_clerk_42"
    assert (await _verifier(audience="my-aud").verify(ok_list)).provider_user_id == "user_clerk_42"


async def test_authorized_party_enforced_when_configured() -> None:
    bad = _sign(_KEY, kid=_KID, claims=_claims(azp="https://rogue.app"))
    with pytest.raises(TokenVerificationError):
        await _verifier(authorized_parties=("https://app.automatedstructure.com",)).verify(bad)

    ok = _sign(_KEY, kid=_KID, claims=_claims(azp="https://app.automatedstructure.com"))
    result = await _verifier(authorized_parties=("https://app.automatedstructure.com",)).verify(ok)
    assert result.provider_session_ref == "sess_clerk_ref"


@pytest.mark.parametrize("missing", ["sub", "email", "sid", "exp"])
async def test_missing_required_claim_fails(missing: str) -> None:
    claims = _claims()
    del claims[missing]
    token = _sign(_KEY, kid=_KID, claims=claims)
    with pytest.raises(TokenVerificationError):
        await _verifier().verify(token)


async def test_unknown_kid_fails_closed() -> None:
    token = _sign(_KEY, kid="nonexistent-kid", claims=_claims())
    with pytest.raises(TokenVerificationError):
        await _verifier().verify(token)


async def test_malformed_jwks_missing_modulus_fails() -> None:
    broken = {"kty": "RSA", "alg": "RS256", "kid": _KID, "e": "AQAB"}  # no "n"
    token = _sign(_KEY, kid=_KID, claims=_claims())
    with pytest.raises(TokenVerificationError):
        await _verifier(keys=[broken]).verify(token)


@pytest.mark.parametrize("alg", ["none", "HS256", "RS512"])
async def test_non_rs256_alg_rejected(alg: str) -> None:
    token = _sign(_KEY, kid=_KID, claims=_claims(), alg=alg)
    with pytest.raises(TokenVerificationError):
        await _verifier().verify(token)


@pytest.mark.parametrize("bad", ["only.two", "not-a-jwt", "a.b.c.d", "@@@.@@@.@@@"])
async def test_malformed_token_fails(bad: str) -> None:
    with pytest.raises(TokenVerificationError):
        await _verifier().verify(bad)


async def test_kid_miss_triggers_refresh_then_succeeds() -> None:
    class _RotatingSource:
        def __init__(self) -> None:
            self.refreshed = 0

        async def get_keys(self) -> Sequence[Jwk]:
            return [_jwk(_OTHER_KEY, _OTHER_KID)]  # stale: lacks the signing kid

        async def refresh(self) -> Sequence[Jwk]:
            self.refreshed += 1
            return [_jwk(_KEY, _KID)]  # fresh: now contains it

    source = _RotatingSource()
    token = _sign(_KEY, kid=_KID, claims=_claims())
    result = await ClerkJwksVerifier(jwks=source, issuer=_ISSUER, clock=lambda: float(_NOW)).verify(
        token
    )
    assert result.provider_user_id == "user_clerk_42"
    assert source.refreshed == 1


async def test_jwks_unavailable_fails_closed() -> None:
    class _DeadSource:
        async def get_keys(self) -> Sequence[Jwk]:
            raise TokenVerificationError("jwks unavailable")

        async def refresh(self) -> Sequence[Jwk]:
            raise TokenVerificationError("jwks unavailable")

    token = _sign(_KEY, kid=_KID, claims=_claims())
    with pytest.raises(TokenVerificationError):
        await ClerkJwksVerifier(jwks=_DeadSource(), issuer=_ISSUER).verify(token)


async def test_error_messages_never_leak_raw_token() -> None:
    secret_token = _sign(_OTHER_KEY, kid=_KID, claims=_claims())  # bad signature
    try:
        await _verifier().verify(secret_token)
    except TokenVerificationError as exc:
        assert secret_token not in str(exc)
    else:  # pragma: no cover - must raise
        raise AssertionError("expected TokenVerificationError")


def test_build_managed_verifier_from_settings() -> None:
    class _S:
        auth_provider_issuer = _ISSUER
        auth_provider_jwks_url = None
        auth_provider_audience = "my-aud"
        auth_provider_authorized_parties = "https://app.automatedstructure.com, "
        auth_provider_email_claim = "email"
        auth_provider_session_claim = "sid"
        auth_provider_mfa_claim = "mfa"

    verifier = build_managed_clerk_verifier(_S())
    assert isinstance(verifier, ClerkJwksVerifier)


def test_build_managed_verifier_requires_issuer() -> None:
    class _S:
        auth_provider_issuer = None

    with pytest.raises(ValueError, match="ISSUER"):
        build_managed_clerk_verifier(_S())
