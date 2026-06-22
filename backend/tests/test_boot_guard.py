"""Boot-guard config-failure tests (Slice 9). DB-state checks run live in CI."""

import pytest

from app.config import Settings
from app.integrations.registry import ProviderKind, mocked_kinds
from app.observability.boot_guard import (
    TENANT_OWNED_TABLES,
    BootGuardError,
    _is_placeholder,
    config_failures,
    enforce_config,
)


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
    assert config_failures(_safe_prod(mock_stripe=True, controlled_demo=True)) == []


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
    assert set(TENANT_OWNED_TABLES) == {"tenants", "tenant_memberships"}


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
