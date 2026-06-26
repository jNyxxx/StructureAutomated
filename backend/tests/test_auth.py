"""Auth/session mapping + revocation tests (Slice 14).

No live Clerk calls: tests use LocalMockClerkVerifier. No raw bearer token should
appear in error envelopes.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth.verifier import LocalMockClerkVerifier, VerifiedClerkClaims
from app.main import create_app
from app.services.auth import AuthMembership, AuthService, AuthUser

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TOKEN = "fake-valid-token"
_SESSION_REF = "sess_clerk_safe_ref"


class _Users:
    def __init__(self) -> None:
        self.rows = {
            ("clerk", "user_clerk_1"): AuthUser(
                id=_USER,
                email="owner@example.com",
                identity_provider="clerk",
                provider_user_id="user_clerk_1",
            )
        }

    async def get_by_identity(
        self, *, identity_provider: str, provider_user_id: str
    ) -> AuthUser | None:
        return self.rows.get((identity_provider, provider_user_id))


class _Memberships:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    async def get_for_user_and_tenant(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> AuthMembership | None:
        if not self.allowed or user_id != _USER or tenant_id != _TENANT:
            return None
        return AuthMembership(
            tenant_id=tenant_id,
            user_id=user_id,
            role="owner",
            membership_version=3,
        )


class _Sessions:
    def __init__(self, revoked: set[str] | None = None) -> None:
        self.revoked = revoked or set()
        self.upserts: list[dict[str, object]] = []
        self.revoked_all: list[uuid.UUID] = []

    async def is_revoked(self, provider_session_ref: str) -> bool:
        return provider_session_ref in self.revoked

    async def upsert_active(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        provider_session_ref: str,
        membership_version: int,
        expires_at: datetime | None,
    ) -> None:
        self.upserts.append(
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "provider_session_ref": provider_session_ref,
                "membership_version": membership_version,
                "expires_at": expires_at,
            }
        )

    async def revoke(self, *, provider_session_ref: str, revoked_at: datetime) -> int:
        self.revoked.add(provider_session_ref)
        return 1

    async def revoke_all_for_user(self, *, user_id: uuid.UUID, revoked_at: datetime) -> int:
        self.revoked_all.append(user_id)
        self.revoked.add(_SESSION_REF)
        return 1


def _service(
    *, memberships: _Memberships | None = None, sessions: _Sessions | None = None
) -> AuthService:
    verifier = LocalMockClerkVerifier(
        {
            _TOKEN: VerifiedClerkClaims(
                provider_user_id="user_clerk_1",
                email="owner@example.com",
                provider_session_ref=_SESSION_REF,
                expires_at=1_800_000_000,
                mfa_verified=True,
            )
        }
    )
    return AuthService(
        verifier=verifier,
        users=_Users(),
        memberships=memberships or _Memberships(),
        sessions=sessions or _Sessions(),
    )


def _client(service: AuthService | None = None) -> TestClient:
    app = create_app()
    app.state.auth_service = service or _service()
    return TestClient(app)


def _headers(token: str = _TOKEN, tenant_id: uuid.UUID = _TENANT) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


def test_valid_token_resolves_principal_user_mapping_and_tenant_membership() -> None:
    sessions = _Sessions()
    resp = _client(_service(sessions=sessions)).post("/auth/session", headers=_headers())

    assert resp.status_code == 200
    principal = resp.json()["principal"]
    assert principal["provider_user_id"] == "user_clerk_1"
    assert principal["user_id"] == str(_USER)
    assert principal["tenant_id"] == str(_TENANT)
    assert principal["role"] == "owner"
    assert principal["membership_version"] == 3
    assert principal["mfa_verified"] is True
    assert sessions.upserts[0]["provider_session_ref"] == _SESSION_REF


def test_missing_token_returns_standard_error_envelope() -> None:
    resp = _client().get("/auth/me", headers={"X-Tenant-ID": str(_TENANT)})

    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert "request_id" in body["error"]


def test_invalid_token_returns_standard_error_without_token_leak() -> None:
    sentinel = "SENTINELTOKEN"
    resp = _client().get("/auth/me", headers=_headers(token=sentinel))

    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert sentinel not in json.dumps(body)


def test_revoked_session_is_denied() -> None:
    sessions = _Sessions(revoked={_SESSION_REF})
    resp = _client(_service(sessions=sessions)).get("/auth/me", headers=_headers())

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_SESSION_REVOKED"


def test_logout_revokes_session_and_next_request_is_denied() -> None:
    sessions = _Sessions()
    client = _client(_service(sessions=sessions))

    logout = client.post("/auth/logout", headers=_headers())
    denied = client.get("/auth/me", headers=_headers())

    assert logout.status_code == 200
    assert logout.json()["revoked"] == 1
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "AUTH_SESSION_REVOKED"


def test_no_membership_blocks_tenant_access() -> None:
    resp = _client(_service(memberships=_Memberships(allowed=False))).get(
        "/auth/me", headers=_headers()
    )

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_ACCESS_DENIED"


def test_wrong_tenant_blocks_access() -> None:
    resp = _client().get("/auth/me", headers=_headers(tenant_id=_OTHER_TENANT))

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_ACCESS_DENIED"


def test_logout_all_revokes_user_sessions() -> None:
    sessions = _Sessions()
    resp = _client(_service(sessions=sessions)).post("/auth/logout-all", headers=_headers())

    assert resp.status_code == 200
    assert resp.json()["revoked"] == 1
    assert sessions.revoked_all == [_USER]


def test_live_local_app_wires_mock_auth_service_only_for_non_production() -> None:
    app = create_app()
    client = TestClient(app)

    resp = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer token-sentinel",
            "X-Tenant-ID": "22222222-2222-2222-2222-222222222222",
        },
    )

    assert resp.status_code == 200
    principal = resp.json()["principal"]
    assert principal["email"] == "owner@example.com"
    assert principal["tenant_id"] == "22222222-2222-2222-2222-222222222222"
    assert principal["role"] == "owner"
    assert principal["mfa_verified"] is True


def test_production_app_does_not_attach_mock_verifier(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.config import get_settings

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MOCK_VERIFIER", "true")
    get_settings.cache_clear()
    try:
        app = create_app()
        # Production must NOT wire the LocalMockClerkVerifier-backed service.
        assert getattr(app.state, "auth_service", None) is None
        # Issuer is unset/None by default → managed verifier also not wired.
        assert getattr(app.state, "clerk_verifier", None) is None
    finally:
        get_settings.cache_clear()


def test_production_wires_clerk_verifier_not_mock(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Managed-auth branch sets clerk_verifier singleton; never sets mock auth_service."""
    from app.auth.clerk_jwks import ClerkJwksVerifier
    from app.config import get_settings

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MOCK_VERIFIER", "false")
    monkeypatch.setenv("AUTH_PROVIDER_ISSUER", "https://clerk.example.com")
    get_settings.cache_clear()
    try:
        app = create_app()
        assert getattr(app.state, "auth_service", None) is None
        assert isinstance(getattr(app.state, "clerk_verifier", None), ClerkJwksVerifier)
    finally:
        get_settings.cache_clear()


def test_managed_auth_service_uses_correct_store_types() -> None:
    """make_managed_auth_service wires verifier singleton and DB-backed repo instances."""
    from app.auth.clerk_jwks import ClerkJwksVerifier, StaticJwksSource
    from app.auth.managed import make_managed_auth_service
    from app.repositories.auth_session_repo import AuthSessionRepository
    from app.repositories.membership_repo import MembershipRepository
    from app.repositories.user_repo import UserRepository

    verifier = ClerkJwksVerifier(jwks=StaticJwksSource([]), issuer="https://clerk.example.com")
    service = make_managed_auth_service(verifier, MagicMock())
    assert isinstance(service, AuthService)
    assert service._verifier is verifier
    assert isinstance(service._users, UserRepository)
    assert isinstance(service._memberships, MembershipRepository)
    assert isinstance(service._sessions, AuthSessionRepository)


def test_current_principal_enforces_mfa_for_platform_admin_role() -> None:
    """enforce_mfa raises MFA_REQUIRED for platform_admin role.

    Currently a no-op in live code because platform_admin is not in the RBAC matrix.
    Wiring is in place; enforcement activates when the role is added.
    """
    from app.auth.mfa import enforce_mfa, mfa_required_roles
    from app.auth.principal import CurrentPrincipal
    from app.config import Settings
    from app.middleware.error_handler import AppError

    principal = CurrentPrincipal(
        provider_user_id="u1",
        provider_session_ref="s1",
        user_id=_USER,
        email="admin@example.com",
        tenant_id=_TENANT,
        role="platform_admin",
        membership_version=1,
        mfa_verified=False,
    )
    settings = Settings(auth_mfa_required_roles="platform_admin")
    with pytest.raises(AppError) as exc_info:
        enforce_mfa(principal, required_roles=mfa_required_roles(settings))
    assert exc_info.value.code == "MFA_REQUIRED"
    assert exc_info.value.status_code == 403


def test_current_principal_mfa_noop_for_existing_roles() -> None:
    """enforce_mfa is a no-op for all 7 current RBAC roles (none match platform_admin)."""
    from app.auth.mfa import enforce_mfa, mfa_required_roles
    from app.auth.principal import CurrentPrincipal
    from app.config import get_settings

    required = mfa_required_roles(get_settings())
    for role in ("owner", "admin", "marketer", "reviewer", "viewer", "billing_admin", "support"):
        principal = CurrentPrincipal(
            provider_user_id="u1",
            provider_session_ref="s1",
            user_id=_USER,
            email="t@example.com",
            tenant_id=_TENANT,
            role=role,
            membership_version=1,
            mfa_verified=False,
        )
        enforce_mfa(principal, required_roles=required)  # must not raise


def test_auth_session_migration_has_no_raw_token_storage_and_forced_rls() -> None:
    src = (
        Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0007_auth_sessions.py"
    ).read_text(encoding="utf-8")

    assert "auth_sessions" in src
    assert "provider_session_ref" in src
    assert "ALTER TABLE auth_sessions FORCE ROW LEVEL SECURITY" in src
    assert "app.auth_context" in src
    assert "membership_version" in src
    assert "raw_token" not in src
    assert "refresh_token" not in src
    assert 'sa.Column("password"' not in src
