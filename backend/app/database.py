"""Async database readiness checks and Alembic head resolution.

Slice 5 establishes the DB connection layer used by readiness. The app connects
via the configured app-role DSN (``DATABASE_URL``) — never the Postgres
superuser in normal runtime. Least-privilege role provisioning (NOSUPERUSER, no
BYPASSRLS) and the pooled, tenant-scoped session helper land in Slice 6; the
production boot guard (Slice 9) enforces the no-superuser / no-BYPASSRLS rules.

Readiness never returns or logs the DSN, credentials, or raw driver errors
(CLAUDE.md rule 14).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.observability.logging import get_logger
from app.ratelimit.redis_backend import check_redis_ready

_logger = get_logger("app.database")
_CONNECT_TIMEOUT_SECONDS = 3.0
_ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"

# Role-safety: the runtime DB role must never be SUPERUSER or have BYPASSRLS.
ROLE_SAFETY_SQL = "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the cached pooled async engine (app-role DSN)."""
    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"timeout": _CONNECT_TIMEOUT_SECONDS},
    )


def _tenant_context_statements(
    tenant_id: UUID | str,
    actor_id: UUID | str | None,
    request_id: str | None,
) -> list[tuple[str, dict[str, str]]]:
    """Transaction-local (SET LOCAL equivalent) context, parameterized and leak-free."""
    statements = [("SELECT set_config('app.current_tenant_id', :v, true)", {"v": str(tenant_id)})]
    if actor_id is not None:
        statements.append(("SELECT set_config('app.actor_id', :v, true)", {"v": str(actor_id)}))
    if request_id is not None:
        statements.append(("SELECT set_config('app.request_id', :v, true)", {"v": str(request_id)}))
    return statements


@asynccontextmanager
async def tenant_session(
    *,
    tenant_id: UUID | str,
    actor_id: UUID | str | None = None,
    request_id: str | None = None,
) -> AsyncIterator[AsyncConnection]:
    """Open a transaction with tenant context set; repositories use this only.

    Uses ``set_config(..., is_local=true)`` so the context is transaction-scoped
    and cannot leak to other transactions on the pooled connection.
    """
    async with get_engine().connect() as conn, conn.begin():
        for sql, params in _tenant_context_statements(tenant_id, actor_id, request_id):
            await conn.execute(text(sql), params)
        yield conn


@asynccontextmanager
async def auth_context_session() -> AsyncIterator[AsyncConnection]:
    """Open a transaction for pre-tenant auth/session lookups.

    Sets ``app.auth_context='on'`` transaction-locally so auth/session rows can
    be checked without setting tenant context before membership resolution. This
    helper is for authentication plumbing only and must never be used for
    tenant business data.
    """
    async with get_engine().connect() as conn, conn.begin():
        await conn.execute(text("SELECT set_config('app.auth_context', 'on', true)"))
        yield conn


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncConnection]:
    """Open a transaction in worker/system context for cross-tenant job claiming.

    Sets ``app.worker_context='on'`` (transaction-local, like tenant context) so
    the worker can claim jobs across tenants under the ``jobs`` RLS policy. This
    is a trusted-infrastructure context set only by the worker claim path — never
    by request handling. Per-job processing must use ``tenant_session`` so normal
    tenant isolation applies while the job runs.
    """
    async with get_engine().connect() as conn, conn.begin():
        await conn.execute(text("SELECT set_config('app.worker_context', 'on', true)"))
        yield conn


async def assert_runtime_role_safe(conn: AsyncConnection) -> None:
    """Raise if the connected role is SUPERUSER or has BYPASSRLS (boot-guard use)."""
    row = (await conn.execute(text(ROLE_SAFETY_SQL))).first()
    if row is None:
        return
    if bool(row[0]) or bool(row[1]):
        raise RuntimeError("Application DB role must not be SUPERUSER or have BYPASSRLS.")


def code_head_revision() -> str | None:
    """Return the latest migration revision defined in code (the Alembic head)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(_ALEMBIC_INI))
    return ScriptDirectory.from_config(config).get_current_head()


async def _current_db_revision(conn: AsyncConnection) -> str | None:
    try:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
    except Exception:
        # Table absent (no migrations applied yet) or unreadable.
        return None
    return row[0] if row else None


async def check_readiness(settings: Settings | None = None) -> dict[str, Any]:
    """Return a readiness result.

    Never leaks the DSN, credentials, Redis URL, or raw driver/backend errors. When
    the DB is not configured the app can still be ready; Redis is checked only
    when the rate-limit backend is configured as Redis.
    """
    settings = settings or get_settings()
    ready = True
    checks: dict[str, str] = {}

    if not settings.is_db_configured or settings.database_url is None:
        checks["database"] = "not_configured"
    else:
        engine = create_async_engine(
            settings.database_url,
            poolclass=NullPool,
            connect_args={"timeout": _CONNECT_TIMEOUT_SECONDS},
        )
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                db_revision = await _current_db_revision(conn)
            at_head = db_revision is not None and db_revision == code_head_revision()
            checks["database"] = "ok"
            checks["migrations"] = "up_to_date" if at_head else "out_of_date"
            ready = ready and at_head
        except Exception:
            # Fixed event only — never the exception text or DSN (may carry credentials).
            _logger.warning("readiness.db_unavailable", extra={"event": "readiness.db_unavailable"})
            checks["database"] = "unavailable"
            ready = False
        finally:
            await engine.dispose()

    rate_limit_backend = settings.rate_limit_backend.strip().lower()
    checks["rate_limit_backend"] = rate_limit_backend
    if rate_limit_backend == "redis":
        if settings.rate_limit_redis_url and await check_redis_ready(settings.rate_limit_redis_url):
            checks["redis"] = "ok"
        else:
            _logger.warning(
                "readiness.redis_unavailable", extra={"event": "readiness.redis_unavailable"}
            )
            checks["redis"] = "unavailable"
            ready = False

    return {"ready": ready, "checks": checks}
