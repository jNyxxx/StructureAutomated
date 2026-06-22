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

# Tenant-owned tables that MUST have ENABLE + FORCE RLS. audit_events is a
# documented exception (stores tenant + platform events; immutable via
# trigger/grants), so it is intentionally NOT listed here.
TENANT_OWNED_TABLES = ("tenants", "tenant_memberships")

_REQUIRED_PROD_SECRETS = ("jwt_secret", "encryption_key", "webhook_secret")
_PLACEHOLDER_MARKERS = ("change_me", "changeme", "placeholder", "todo", "xxx")
_ZERO_UUID = "00000000-0000-0000-0000-000000000000"


class BootGuardError(RuntimeError):
    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__("Boot guard failed: " + "; ".join(failures))


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    v = value.strip().lower()
    return v == "" or len(v) < 8 or any(marker in v for marker in _PLACEHOLDER_MARKERS)


def config_failures(settings: Settings) -> list[str]:
    """Sync configuration checks. Empty outside production."""
    if settings.app_env != "production":
        return []
    failures: list[str] = []
    mocks = mocked_kinds(settings)
    if mocks and not settings.controlled_demo:
        failures.append(f"mock providers enabled in production: {sorted(k.value for k in mocks)}")
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
