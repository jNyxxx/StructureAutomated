"""Production boot guard.

Fails boot (in production) on unsafe configuration or database state. Config
checks are sync; database checks are async. Non-production environments are
allowed to run mocks, so the guard is a no-op outside production.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import Settings
from app.database import ROLE_SAFETY_SQL, code_head_revision
from app.integrations.registry import mocked_kinds
from app.services.email_provider import (
    MOCK_EMAIL_PROVIDER,
    RESEND_EMAIL_PROVIDER,
    resend_config_failures,
)

# Tenant-owned tables that MUST have ENABLE + FORCE RLS, verified at boot.
#
# Source of truth: every table the migrations force RLS on — the
# ``apply_forced_rls()`` callers in migrations/versions/* plus the literal
# ``ALTER TABLE ... ENABLE/FORCE ROW LEVEL SECURITY`` statements. That set is 30
# tables; ``audit_events`` is a documented exception (stores tenant + platform
# events; immutable via trigger/grants; non-standard policy), so it is
# intentionally NOT listed here, leaving the 29 below. Adding a new tenant-owned
# table requires adding it both to a migration and to this tuple (the
# test suite fails closed if a tenant_id model table is missing here).
TENANT_OWNED_TABLES = (
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
)

_REQUIRED_PROD_SECRETS = ("jwt_secret", "encryption_key", "webhook_secret")
_PLACEHOLDER_MARKERS = ("change_me", "changeme", "placeholder", "todo", "xxx")
_ZERO_UUID = "00000000-0000-0000-0000-000000000000"
# Managed auth provider identifiers acceptable in production (Clerk-backed).
_MANAGED_AUTH_PROVIDERS = ("managed", "clerk")
# Forbidden host markers for public auth URLs in production (owner decision:
# no localhost / preview / wildcard origins in production).
_FORBIDDEN_URL_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", "*")  # noqa: S104 - URL substrings


class BootGuardError(RuntimeError):
    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__("Boot guard failed: " + "; ".join(failures))


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    v = value.strip().lower()
    return v == "" or len(v) < 8 or any(marker in v for marker in _PLACEHOLDER_MARKERS)


def _is_https_nonlocal(url: str | None) -> bool:
    if url is None:
        return False
    u = url.strip().lower()
    return u.startswith("https://") and not any(m in u for m in _FORBIDDEN_URL_MARKERS)


def _is_redis_url(url: str | None) -> bool:
    if _is_placeholder(url) or url is None:
        return False
    u = url.strip().lower()
    return u.startswith(("redis://", "rediss://"))


def _email_provider_failures(settings: Settings) -> list[str]:
    """Email-provider config checks for production and staging live-send attempts.

    P3-5f adds only a fail-closed Resend skeleton. Provider selection must not
    silently fall back to mock. controlled_demo must not bypass live email
    delivery requirements.
    """
    failures: list[str] = []
    provider = settings.email_provider.strip().lower()
    if provider not in {MOCK_EMAIL_PROVIDER, RESEND_EMAIL_PROVIDER}:
        failures.append(
            f"email_provider '{settings.email_provider}' has no approved live adapter in this build"
        )
    if settings.live_email_sending_enabled:
        if provider != RESEND_EMAIL_PROVIDER:
            failures.append("live_email_sending_enabled requires EMAIL_PROVIDER=resend")
        failures.extend(resend_config_failures(settings))
    return failures


def _auth_failures(settings: Settings) -> list[str]:
    """Production managed-auth (Clerk) config checks.

    Auth is NEVER mockable in production: controlled_demo may permit mock
    billing/mailbox/dns/research, but it must not bypass real auth. Public
    issuer/JWKS values must be present + https + non-placeholder; the secret /
    publishable keys must be non-placeholder (real values come from the secrets
    backend, not committed). JWKS reachability is intentionally NOT checked here
    (no network at boot); it is a documented runtime/manual verification.
    """
    failures: list[str] = []
    if settings.mock_verifier:
        failures.append(
            "mock_verifier (mock auth) must be false in production; "
            "controlled_demo does not bypass auth"
        )
    if settings.auth_provider not in _MANAGED_AUTH_PROVIDERS:
        failures.append(
            f"auth_provider must be a managed provider {_MANAGED_AUTH_PROVIDERS} in production "
            f"(got '{settings.auth_provider}')"
        )
    if _is_placeholder(settings.auth_provider_issuer):
        failures.append("AUTH_PROVIDER_ISSUER is blank or placeholder")
    elif not _is_https_nonlocal(settings.auth_provider_issuer):
        failures.append("AUTH_PROVIDER_ISSUER must be an https non-localhost URL in production")
    jwks_url = settings.auth_provider_jwks_url
    if jwks_url is not None and not _is_https_nonlocal(jwks_url):
        failures.append("AUTH_PROVIDER_JWKS_URL must be an https non-localhost URL in production")
    if _is_placeholder(settings.auth_provider_secret_key):
        failures.append("AUTH_PROVIDER_SECRET_KEY is blank or placeholder")
    if _is_placeholder(settings.auth_provider_publishable_key):
        failures.append("AUTH_PROVIDER_PUBLISHABLE_KEY is blank or placeholder")
    return failures


def config_failures(settings: Settings) -> list[str]:
    """Sync configuration checks.

    Production gets the full boot guard. Staging gets the email live-send guard
    so live delivery cannot be accidentally toggled there before the approved
    provider gates clear.
    """
    if settings.app_env == "staging":
        return _email_provider_failures(settings)
    if settings.app_env != "production":
        return []
    failures: list[str] = []
    mocks = mocked_kinds(settings)
    if mocks and not settings.controlled_demo:
        failures.append(f"mock providers enabled in production: {sorted(k.value for k in mocks)}")
    # controlled_demo is an owner-gated escape hatch that permits mock providers
    # under APP_ENV=production. It must never be silent: require a recorded
    # owner-approval attestation, and fail closed when it is missing/placeholder.
    if settings.controlled_demo and _is_placeholder(settings.controlled_demo_approved_by):
        failures.append(
            "controlled_demo requires controlled_demo_approved_by (owner-approval attestation)"
        )
    for name in _REQUIRED_PROD_SECRETS:
        if _is_placeholder(getattr(settings, name)):
            failures.append(f"required secret '{name}' is blank or placeholder")
    if not settings.cookie_secure:
        failures.append("cookie_secure must be true in production")
    if not settings.https_only:
        failures.append("https_only must be true in production")
    if not settings.csrf_enabled:
        failures.append("csrf_enabled must be true in production")
    if settings.cors_allow_all:
        failures.append("cors_allow_all must be false in production")
    if settings.secret_backend != "aws":  # noqa: S105 - backend selector, not a secret
        failures.append("secret_backend must be 'aws' in production")
    if settings.rate_limit_backend != "redis":
        failures.append("rate_limit_backend must be 'redis' in production")
    if not _is_redis_url(settings.rate_limit_redis_url):
        failures.append("RATE_LIMIT_REDIS_URL must be a non-placeholder redis:// or rediss:// URL")
    failures.extend(_email_provider_failures(settings))
    failures.extend(_auth_failures(settings))
    return failures


async def _scalar(conn: AsyncConnection, sql: str, params: dict[str, str] | None = None) -> object:
    try:
        return (await conn.execute(text(sql), params or {})).scalar()
    except Exception:
        return None


async def database_failures(conn: AsyncConnection, settings: Settings) -> list[str]:
    """Async database-state checks (run in production when a DB is configured)."""
    failures: list[str] = []

    row = (await conn.execute(text(ROLE_SAFETY_SQL))).first()
    if row is not None and (bool(row[0]) or bool(row[1])):
        failures.append("DB role is SUPERUSER or has BYPASSRLS")

    await conn.execute(
        text("SELECT set_config('app.current_tenant_id', :v, true)"), {"v": _ZERO_UUID}
    )
    got = await _scalar(conn, "SELECT current_setting('app.current_tenant_id', true)")
    if got != _ZERO_UUID:
        failures.append("tenant context could not be verified")

    for table in TENANT_OWNED_TABLES:
        r = (
            await conn.execute(
                text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = :t"),
                {"t": table},
            )
        ).first()
        if r is None or not bool(r[0]) or not bool(r[1]):
            failures.append(f"table '{table}' lacks ENABLE/FORCE row level security")

    db_head = await _scalar(conn, "SELECT version_num FROM alembic_version")
    if db_head != code_head_revision():
        failures.append("database migration head does not match code head")

    return failures


def enforce_config(settings: Settings) -> None:
    failures = config_failures(settings)
    if failures:
        raise BootGuardError(failures)
