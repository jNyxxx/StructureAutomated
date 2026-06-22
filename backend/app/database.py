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

from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.observability.logging import get_logger

_logger = get_logger("app.database")
_CONNECT_TIMEOUT_SECONDS = 3.0
_ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


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

    Never leaks the DSN, credentials, or raw driver errors. When the DB is not
    configured the app is still considered ready (the API can serve without it).
    """
    settings = settings or get_settings()
    if not settings.is_db_configured or settings.database_url is None:
        return {"ready": True, "checks": {"database": "not_configured"}}

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
        return {
            "ready": at_head,
            "checks": {
                "database": "ok",
                "migrations": "up_to_date" if at_head else "out_of_date",
            },
        }
    except Exception:
        # Fixed event only — never the exception text or DSN (may carry credentials).
        _logger.warning("readiness.db_unavailable", extra={"event": "readiness.db_unavailable"})
        return {"ready": False, "checks": {"database": "unavailable"}}
    finally:
        await engine.dispose()
