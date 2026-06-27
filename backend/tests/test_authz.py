"""RBAC, object authorization, and support-access tests (Slice 15)."""

import uuid
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.auth.principal import CurrentPrincipal
from app.config import get_settings
from app.middleware.error_handler import AppError
from app.services.authz import (
    CAN_ACCESS_PLATFORM,
    CAN_APPROVE_DRAFT,
    CAN_CREATE_CAMPAIGN,
    CAN_GRANT_SUPPORT_ACCESS,
    CAN_IMPORT_CONTACTS,
    CAN_MANAGE_BILLING,
    CAN_MANAGE_INTEGRATIONS,
    CAN_MANAGE_TEAM,
    CAN_READ_AUDIT,
    CAN_READ_DASHBOARD,
    CAN_REVIEW_DRAFT,
    CAN_RUN_CAMPAIGN,
    CAN_SCHEDULE_SEND,
    ROLE_PERMISSIONS,
    ObjectAuthorizationService,
    RBACService,
    SupportAccessGrant,
    SupportAccessService,
    TenantOwnedObject,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_OWNER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_SUPPORT = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_NOW = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)
_ALL_PERMISSIONS = {
    CAN_READ_DASHBOARD,
    CAN_IMPORT_CONTACTS,
    CAN_CREATE_CAMPAIGN,
    CAN_RUN_CAMPAIGN,
    CAN_REVIEW_DRAFT,
    CAN_APPROVE_DRAFT,
    CAN_SCHEDULE_SEND,
    CAN_MANAGE_TEAM,
    CAN_MANAGE_BILLING,
    CAN_READ_AUDIT,
    CAN_MANAGE_INTEGRATIONS,
    CAN_GRANT_SUPPORT_ACCESS,
}


def _principal(role: str, *, user_id: uuid.UUID = _OWNER) -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=user_id,
        email="user@example.com",
        tenant_id=_TENANT,
        role=role,
        membership_version=1,
        mfa_verified=True,
    )


class _SupportStore:
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, SupportAccessGrant] = {}

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        support_user_id: uuid.UUID,
        granted_by_user_id: uuid.UUID,
        reason: str,
        scope: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> SupportAccessGrant:
        grant = SupportAccessGrant(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            support_user_id=support_user_id,
            granted_by_user_id=granted_by_user_id,
            reason=reason,
            scope=scope,
            expires_at=expires_at,
            revoked_at=None,
            created_at=created_at,
        )
        self.rows[grant.id] = grant
        return grant

    async def get_active(
        self,
        *,
        tenant_id: uuid.UUID,
        support_user_id: uuid.UUID,
        scope: str,
        now: datetime,
    ) -> SupportAccessGrant | None:
        for grant in self.rows.values():
            if (
                grant.tenant_id == tenant_id
                and grant.support_user_id == support_user_id
                and grant.scope == scope
                and grant.is_active(now)
            ):
                return grant
        return None

    async def revoke(
        self, *, grant_id: uuid.UUID, revoked_at: datetime
    ) -> SupportAccessGrant | None:
        grant = self.rows.get(grant_id)
        if grant is None:
            return None
        revoked = replace(grant, revoked_at=revoked_at)
        self.rows[grant_id] = revoked
        return revoked


@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        ("owner", _ALL_PERMISSIONS),
        (
            "admin",
            _ALL_PERMISSIONS - {CAN_MANAGE_BILLING, CAN_GRANT_SUPPORT_ACCESS},
        ),
        (
            "marketer",
            {
                CAN_READ_DASHBOARD,
                CAN_IMPORT_CONTACTS,
                CAN_CREATE_CAMPAIGN,
                CAN_RUN_CAMPAIGN,
                CAN_REVIEW_DRAFT,
                CAN_SCHEDULE_SEND,
            },
        ),
        ("reviewer", {CAN_REVIEW_DRAFT, CAN_APPROVE_DRAFT}),
        ("viewer", {CAN_READ_DASHBOARD}),
        ("billing_admin", {CAN_MANAGE_BILLING}),
        # platform_admin has no tenant permissions — only the platform:access perm,
        # which is not in _ALL_PERMISSIONS (tenant universe). Default-deny for all
        # tenant permissions is proven by the loop below.
        ("platform_admin", set()),
        ("unknown", set()),
    ],
)
def test_role_permission_matrix_and_default_deny(role: str, allowed: set[str]) -> None:
    rbac = RBACService()
    for permission in _ALL_PERMISSIONS:
        assert rbac.has_permission(role, permission) is (permission in allowed)

    denied = _ALL_PERMISSIONS - allowed
    if denied:
        with pytest.raises(AppError) as exc:
            rbac.require(_principal(role), sorted(denied)[0])
        assert exc.value.status_code == 403
        assert exc.value.code == "FORBIDDEN"


def test_object_authorization_allows_same_tenant_and_action_permission() -> None:
    ObjectAuthorizationService().require_tenant_owner(
        principal=_principal("owner"),
        obj=TenantOwnedObject(id=uuid.uuid4(), tenant_id=_TENANT),
        action=CAN_CREATE_CAMPAIGN,
        rbac=RBACService(),
    )


@pytest.mark.parametrize("obj", [None, TenantOwnedObject(id=uuid.uuid4(), tenant_id=_OTHER_TENANT)])
def test_object_authorization_denies_missing_or_cross_tenant_object(
    obj: TenantOwnedObject | None,
) -> None:
    with pytest.raises(AppError) as exc:
        ObjectAuthorizationService().require_tenant_owner(principal=_principal("owner"), obj=obj)

    assert exc.value.status_code == 403
    assert exc.value.code == "OBJECT_ACCESS_DENIED"
    assert "not found" in exc.value.message.lower()


async def test_support_access_requires_owner_permission_and_positive_ttl() -> None:
    service = SupportAccessService(store=_SupportStore(), rbac=RBACService())

    with pytest.raises(AppError) as denied:
        await service.grant(
            principal=_principal("admin"),
            support_user_id=_SUPPORT,
            reason="debug tenant issue",
            scope="read:audit",
            now=_NOW,
        )
    assert denied.value.status_code == 403

    with pytest.raises(AppError) as invalid_ttl:
        await service.grant(
            principal=_principal("owner"),
            support_user_id=_SUPPORT,
            reason="debug tenant issue",
            scope="read:audit",
            now=_NOW,
            ttl=timedelta(0),
        )
    assert invalid_ttl.value.code == "INVALID_SUPPORT_GRANT"


async def test_support_access_grant_use_revoke_and_audit() -> None:
    audits: list[dict[str, object]] = []

    async def audit_record(**kwargs: object) -> None:
        audits.append(kwargs)

    store = _SupportStore()
    service = SupportAccessService(store=store, rbac=RBACService(), audit_record=audit_record)
    owner = _principal("owner")
    support = _principal("support", user_id=_SUPPORT)

    grant = await service.grant(
        principal=owner,
        support_user_id=_SUPPORT,
        reason="debug tenant issue",
        scope="read:audit",
        now=_NOW,
    )
    used = await service.require_active(principal=support, scope="read:audit", now=_NOW)
    revoked = await service.revoke(
        principal=owner, grant_id=grant.id, now=_NOW + timedelta(minutes=5)
    )

    assert grant.expires_at == _NOW + timedelta(minutes=60)
    assert used.id == grant.id
    assert revoked.revoked_at == _NOW + timedelta(minutes=5)
    assert [a["event_type"] for a in audits] == [
        "support_access.granted",
        "support_access.used",
        "support_access.revoked",
    ]
    assert "debug tenant issue" not in str(audits)  # no free-text reason/PII in audit details


async def test_support_access_no_explicit_grant_denied_and_revoked_grant_denied() -> None:
    store = _SupportStore()
    service = SupportAccessService(store=store, rbac=RBACService())
    owner = _principal("owner")
    support = _principal("support", user_id=_SUPPORT)

    with pytest.raises(AppError) as missing:
        await service.require_active(principal=support, scope="read:audit", now=_NOW)
    assert missing.value.code == "SUPPORT_ACCESS_DENIED"

    grant = await service.grant(
        principal=owner,
        support_user_id=_SUPPORT,
        reason="debug tenant issue",
        scope="read:audit",
        now=_NOW,
    )
    await service.revoke(principal=owner, grant_id=grant.id, now=_NOW + timedelta(minutes=1))

    with pytest.raises(AppError) as revoked:
        await service.require_active(
            principal=support, scope="read:audit", now=_NOW + timedelta(minutes=2)
        )
    assert revoked.value.code == "SUPPORT_ACCESS_DENIED"


async def test_support_access_expired_grant_denied() -> None:
    store = _SupportStore()
    service = SupportAccessService(store=store, rbac=RBACService())
    owner = _principal("owner")
    support = _principal("support", user_id=_SUPPORT)

    await service.grant(
        principal=owner,
        support_user_id=_SUPPORT,
        reason="debug tenant issue",
        scope="read:audit",
        now=_NOW,
        ttl=timedelta(minutes=1),
    )

    with pytest.raises(AppError) as expired:
        await service.require_active(
            principal=support, scope="read:audit", now=_NOW + timedelta(minutes=2)
        )
    assert expired.value.code == "SUPPORT_ACCESS_DENIED"


def test_platform_admin_has_only_platform_access_permission() -> None:
    rbac = RBACService()
    # platform_admin has the platform:access permission
    assert rbac.has_permission("platform_admin", CAN_ACCESS_PLATFORM) is True
    # platform_admin has NO tenant permissions
    for perm in _ALL_PERMISSIONS:
        assert (
            rbac.has_permission("platform_admin", perm) is False
        ), f"platform_admin must not have tenant permission {perm!r}"
    # owner does NOT get platform:access (universes are separate)
    assert rbac.has_permission("owner", CAN_ACCESS_PLATFORM) is False
    # platform_admin is registered in the RBAC matrix
    assert "platform_admin" in ROLE_PERMISSIONS


async def test_platform_admin_cannot_grant_support_access_or_bypass_require_active() -> None:
    service = SupportAccessService(store=_SupportStore(), rbac=RBACService())
    platform = _principal("platform_admin")

    # platform_admin cannot grant support access (lacks CAN_GRANT_SUPPORT_ACCESS)
    with pytest.raises(AppError) as exc:
        await service.grant(
            principal=platform,
            support_user_id=_SUPPORT,
            reason="platform attempt",
            scope="read:audit",
            now=_NOW,
        )
    assert exc.value.status_code == 403
    assert exc.value.code == "FORBIDDEN"

    # platform_admin cannot bypass require_active (no active grant → denied)
    with pytest.raises(AppError) as exc2:
        await service.require_active(principal=platform, scope="read:audit", now=_NOW)
    assert exc2.value.code == "SUPPORT_ACCESS_DENIED"


def test_support_access_migration_shape_and_forced_rls() -> None:
    src = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0008_support_access_grants.py"
    ).read_text(encoding="utf-8")

    for column in (
        "tenant_id",
        "support_user_id",
        "granted_by_user_id",
        "reason",
        "scope",
        "expires_at",
        "revoked_at",
        "created_at",
    ):
        assert column in src
    assert "nullable=False" in src
    assert "ALTER TABLE support_access_grants ENABLE ROW LEVEL SECURITY" in src
    assert "ALTER TABLE support_access_grants FORCE ROW LEVEL SECURITY" in src
    assert "tenant_id = current_setting('app.current_tenant_id', true)::uuid" in src
    assert "raw_token" not in src
    assert 'sa.Column("secret"' not in src


def test_platform_admin_role_migration_shape() -> None:
    src = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "00022_platform_admin_role.py"
    ).read_text(encoding="utf-8")

    assert "00022_platform_admin_role" in src
    assert "00021_outcomes" in src  # down_revision
    assert "platform_admin" in src
    assert "ck_tenant_memberships_role" in src
    # must not touch RLS, policies, or other tables
    assert "ENABLE ROW LEVEL SECURITY" not in src
    assert "FORCE ROW LEVEL SECURITY" not in src
    assert "CREATE POLICY" not in src
    assert "DROP POLICY" not in src
    # downgrade must restore original 6-role constraint
    assert "def downgrade" in src


def test_platform_admin_role_migration_offline_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://app_user:example@localhost:5432/automatedstructure"
    )
    get_settings.cache_clear()
    try:
        config = Config(str(backend_root / "alembic.ini"))
        buffer = StringIO()
        with redirect_stdout(buffer):
            command.upgrade(config, "00021_outcomes:00022_platform_admin_role", sql=True)
        sql = buffer.getvalue()
    finally:
        get_settings.cache_clear()

    assert "'platform_admin'" in sql
    assert "ck_tenant_memberships_role" in sql
    # must not alter RLS or policies in this migration
    assert "ENABLE ROW LEVEL SECURITY" not in sql
    assert "FORCE ROW LEVEL SECURITY" not in sql


def test_support_access_offline_sql_contains_forced_rls_and_tenant_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://app_user:example@localhost:5432/automatedstructure"
    )
    get_settings.cache_clear()
    try:
        config = Config(str(backend_root / "alembic.ini"))
        buffer = StringIO()

        with redirect_stdout(buffer):
            command.upgrade(config, "0007_auth_sessions:0008_support_access_grants", sql=True)

        sql = buffer.getvalue()
    finally:
        get_settings.cache_clear()
    assert "tenant_id UUID NOT NULL" in sql
    assert "ALTER TABLE support_access_grants ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE support_access_grants FORCE ROW LEVEL SECURITY" in sql
    assert "tenant_id = current_setting('app.current_tenant_id', true)::uuid" in sql
