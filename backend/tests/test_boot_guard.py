"""Boot-guard config-failure tests (Slice 9; RLS coverage + controlled_demo
attestation hardened in P3-1a). DB-state checks also run live in CI; the
database_failures() tests here use a fake connection so they stay deterministic
without Postgres."""

import pytest

from app.config import Settings
from app.database import code_head_revision
from app.integrations.registry import ProviderKind, mocked_kinds, registry
from app.models import Base
from app.observability.boot_guard import (
    _ZERO_UUID,
    TENANT_OWNED_TABLES,
    BootGuardError,
    _is_placeholder,
    config_failures,
    database_failures,
    enforce_config,
)

# Canonical set of tenant-owned tables the boot guard must verify at runtime
# (the 30 forced-RLS tables minus the documented audit_events exception).
EXPECTED_TENANT_OWNED = {
    "auth_sessions",
    "campaign_contacts",
    "campaign_roi_assumptions",
    "campaigns",
    "compliance_profiles",
    "contact_import_rows",
    "contact_imports",
    "contacts",
    "draft_evidence",
    "drafts",
    "followup_rules",
    "followup_schedules",
    "idempotency_keys",
    "integration_credentials",
    "jobs",
    "knowledge_chunks",
    "knowledge_documents",
    "outbound_messages",
    "outcome_events",
    "research_artifacts",
    "research_runs",
    "review_items",
    "safety_gate_results",
    "send_gate_results",
    "support_access_grants",
    "suppressions",
    "tenant_memberships",
    "tenant_subscriptions",
    "tenants",
}


class _FakeResult:
    def __init__(self, first: object = None, scalar: object = None) -> None:
        self._first = first
        self._scalar = scalar

    def first(self) -> object:
        return self._first

    def scalar(self) -> object:
        return self._scalar


class _FakeConn:
    """Minimal AsyncConnection stand-in for database_failures() RLS-loop tests.

    Dispatches by SQL substring so the per-table pg_class lookups can be driven
    from ``rls`` (table -> (relrowsecurity, relforcerowsecurity)). Defaults model
    a safe role, verified tenant context, and a matching migration head so only
    the RLS state under test produces failures.
    """

    def __init__(self, rls: dict[str, tuple[bool, bool]]) -> None:
        self._rls = rls

    async def execute(self, clause: object, params: dict[str, str] | None = None) -> _FakeResult:
        sql = str(clause)
        if "pg_roles" in sql:  # ROLE_SAFETY_SQL -> (rolsuper, rolbypassrls)
            return _FakeResult(first=(False, False))
        if "set_config" in sql:
            return _FakeResult()
        if "current_setting" in sql:
            return _FakeResult(scalar=_ZERO_UUID)
        if "pg_class" in sql:
            table = (params or {})["t"]
            enabled, forced = self._rls.get(table, (True, True))
            return _FakeResult(first=(enabled, forced))
        if "alembic_version" in sql:
            return _FakeResult(scalar=code_head_revision())
        return _FakeResult()


def _safe_prod(**override: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "production",
        "mock_stripe": False,
        "mock_mailbox": False,
        "mock_dns": False,
        "mock_verifier": False,
        "mock_research": False,
        "controlled_demo": False,
        "jwt_secret": "prod-jwt-0123456789abcd",
        "encryption_key": "prod-enc-0123456789abcd",
        "webhook_secret": "prod-whk-0123456789abcd",
        "cookie_secure": True,
        "csrf_enabled": True,
        "https_only": True,
        "cors_allow_all": False,
        "secret_backend": "aws",
        "auth_provider": "managed",
        "auth_provider_issuer": "https://clerk.example.com",
        "auth_provider_secret_key": "sk_live_0123456789abcdef",
        "auth_provider_publishable_key": "pk_live_0123456789abcdef",
    }
    base.update(override)
    return Settings(**base)  # type: ignore[arg-type]


def test_non_production_is_never_guarded() -> None:
    assert config_failures(Settings(app_env="local", mock_stripe=True)) == []


def test_safe_production_passes() -> None:
    assert config_failures(_safe_prod()) == []
    enforce_config(_safe_prod())  # does not raise


def test_mocks_in_production_fail_unless_controlled_demo() -> None:
    failures = config_failures(_safe_prod(mock_stripe=True))
    assert any("mock providers" in f for f in failures)
    # controlled_demo now also requires a recorded owner-approval attestation.
    assert (
        config_failures(
            _safe_prod(
                mock_stripe=True,
                controlled_demo=True,
                controlled_demo_approved_by="owner:ops (P3-1a 2026-06-26)",
            )
        )
        == []
    )


def test_placeholder_secret_fails() -> None:
    failures = config_failures(_safe_prod(jwt_secret="CHANGE_ME_PLACEHOLDER"))
    assert any("jwt_secret" in f for f in failures)


def test_unsafe_security_toggles_fail() -> None:
    failures = config_failures(
        _safe_prod(cookie_secure=False, https_only=False, cors_allow_all=True)
    )
    joined = " ".join(failures)
    assert "cookie_secure" in joined and "https_only" in joined and "cors_allow_all" in joined


def test_enforce_config_raises_on_unsafe_production() -> None:
    with pytest.raises(BootGuardError):
        enforce_config(_safe_prod(cookie_secure=False))


def test_local_secret_backend_fails_in_production() -> None:
    failures = config_failures(_safe_prod(secret_backend="local"))
    assert any("secret_backend" in f for f in failures)


def test_audit_events_exempt_from_forced_rls_check() -> None:
    assert "audit_events" not in TENANT_OWNED_TABLES
    assert set(TENANT_OWNED_TABLES) == EXPECTED_TENANT_OWNED


def test_tenant_owned_set_is_exact() -> None:
    # Pins the canonical 29-table coverage; add/remove drift fails closed.
    assert len(TENANT_OWNED_TABLES) == 29
    assert len(set(TENANT_OWNED_TABLES)) == 29  # no duplicates
    assert set(TENANT_OWNED_TABLES) == EXPECTED_TENANT_OWNED


def test_boot_guard_covers_every_model_tenant_table() -> None:
    # Drift-proof: every ORM table carrying tenant_id must be verified by the
    # boot guard (audit_events is the one documented exception).
    model_tenant_tables = {
        name for name, table in Base.metadata.tables.items() if "tenant_id" in table.columns
    }
    missing = (model_tenant_tables - {"audit_events"}) - set(TENANT_OWNED_TABLES)
    assert not missing, f"boot guard does not verify tenant tables: {sorted(missing)}"


async def test_all_tables_rls_ok_passes_database_check() -> None:
    conn = _FakeConn(rls={})  # every table defaults to (enabled=True, forced=True)
    failures = await database_failures(conn, Settings())  # type: ignore[arg-type]
    assert not any("row level security" in f for f in failures)


async def test_rls_not_enabled_fails_database_check() -> None:
    conn = _FakeConn(rls={"contacts": (False, True)})
    failures = await database_failures(conn, Settings())  # type: ignore[arg-type]
    assert any("contacts" in f and "row level security" in f for f in failures)


async def test_rls_not_forced_fails_database_check() -> None:
    conn = _FakeConn(rls={"outbound_messages": (True, False)})
    failures = await database_failures(conn, Settings())  # type: ignore[arg-type]
    assert any("outbound_messages" in f and "row level security" in f for f in failures)


def test_controlled_demo_without_attestation_fails_closed() -> None:
    failures = config_failures(_safe_prod(mock_stripe=True, controlled_demo=True))
    assert any("controlled_demo" in f and "attestation" in f for f in failures)


def test_controlled_demo_with_attestation_passes() -> None:
    failures = config_failures(
        _safe_prod(
            mock_stripe=True,
            controlled_demo=True,
            controlled_demo_approved_by="owner:ops (P3-1a 2026-06-26)",
        )
    )
    assert failures == []


def test_controlled_demo_placeholder_attestation_fails() -> None:
    failures = config_failures(
        _safe_prod(
            mock_stripe=True,
            controlled_demo=True,
            controlled_demo_approved_by="CHANGE_ME",
        )
    )
    assert any("controlled_demo" in f for f in failures)


def test_controlled_demo_requires_attestation_even_without_mocks() -> None:
    # No mock providers, but controlled_demo set without an approver still fails.
    failures = config_failures(_safe_prod(controlled_demo=True))
    assert any("controlled_demo" in f and "attestation" in f for f in failures)


def test_missing_auth_issuer_fails() -> None:
    failures = config_failures(_safe_prod(auth_provider_issuer=None))
    assert any("AUTH_PROVIDER_ISSUER" in f for f in failures)


def test_placeholder_auth_issuer_fails() -> None:
    failures = config_failures(_safe_prod(auth_provider_issuer="CHANGE_ME_PLACEHOLDER"))
    assert any("AUTH_PROVIDER_ISSUER" in f for f in failures)


def test_non_https_or_localhost_issuer_fails() -> None:
    http = config_failures(_safe_prod(auth_provider_issuer="http://clerk.example.com"))
    local = config_failures(_safe_prod(auth_provider_issuer="https://localhost:3000"))
    assert any("AUTH_PROVIDER_ISSUER" in f and "https" in f for f in http)
    assert any("AUTH_PROVIDER_ISSUER" in f and "https" in f for f in local)


def test_bad_jwks_url_fails_but_default_ok() -> None:
    bad = config_failures(_safe_prod(auth_provider_jwks_url="http://localhost/jwks.json"))
    assert any("AUTH_PROVIDER_JWKS_URL" in f for f in bad)
    # Unset JWKS URL is fine (defaults to {issuer}/.well-known/jwks.json).
    assert config_failures(_safe_prod(auth_provider_jwks_url=None)) == []


def test_placeholder_auth_secret_and_publishable_keys_fail() -> None:
    sk = config_failures(_safe_prod(auth_provider_secret_key="CHANGE_ME_PLACEHOLDER"))
    pk = config_failures(_safe_prod(auth_provider_publishable_key=None))
    assert any("AUTH_PROVIDER_SECRET_KEY" in f for f in sk)
    assert any("AUTH_PROVIDER_PUBLISHABLE_KEY" in f for f in pk)


def test_non_managed_auth_provider_fails() -> None:
    failures = config_failures(_safe_prod(auth_provider="mock"))
    assert any("auth_provider must be a managed provider" in f for f in failures)


def test_mock_verifier_fails_in_production() -> None:
    failures = config_failures(_safe_prod(mock_verifier=True))
    assert any("mock_verifier" in f for f in failures)


def test_controlled_demo_does_not_bypass_mock_auth() -> None:
    # Even a fully-attested controlled_demo cannot run mock auth in production.
    failures = config_failures(
        _safe_prod(
            mock_verifier=True,
            controlled_demo=True,
            controlled_demo_approved_by="owner:ops (P3-3b 2026-06-26)",
        )
    )
    assert any("mock_verifier" in f and "controlled_demo does not bypass" in f for f in failures)


def test_adapter_registry_has_no_live_provider_paths() -> None:
    # controlled_demo cannot reach a live provider: the registry is empty, so
    # resolution raises before any live factory runs.
    assert registry._factories == {}
    with pytest.raises(KeyError):
        registry.resolve(ProviderKind.STRIPE, Settings())


def test_placeholder_detection() -> None:
    assert _is_placeholder(None)
    assert _is_placeholder("")
    assert _is_placeholder("x")
    assert _is_placeholder("CHANGE_ME_PLACEHOLDER")
    assert not _is_placeholder("a-strong-enough-secret-value")


def test_mocked_kinds_reflects_flags() -> None:
    settings = Settings(app_env="local", mock_stripe=True, mock_dns=False)
    kinds = mocked_kinds(settings)
    assert ProviderKind.STRIPE in kinds
    assert ProviderKind.DNS not in kinds
