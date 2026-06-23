"""Alembic migration environment (async)."""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Make the `app` package importable when alembic runs from the backend dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM models yet (Slice 5 creates extensions only). Autogenerate is unused.
target_metadata = None


# Offline `--sql` rendering never opens a connection, so a real DATABASE_URL is
# not required. Fall back to a non-connecting placeholder DSN (same Postgres
# dialect, so DDL renders identically) when none is configured — this is what
# lets CI render the migration chain to SQL without a database. ONLINE migrations
# stay strict and still require a real DSN.
_OFFLINE_FALLBACK_URL = "postgresql+asyncpg://offline:offline@offline/automatedstructure"


def _database_url() -> str:
    """Strict DSN for ONLINE migrations — a real connection is required."""
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured; cannot run migrations.")
    return url


def _offline_url() -> str:
    """DSN for OFFLINE ``--sql`` rendering; falls back to a placeholder when unset."""
    return get_settings().database_url or _OFFLINE_FALLBACK_URL


def _run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    engine = create_async_engine(_database_url(), poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=_offline_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(_run_async_migrations())
