"""Worker boot-guard entrypoint.

The worker loop (Slice 13) calls ``boot_worker()`` before processing jobs so the
worker enforces the same production safety guard as the API.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.database import get_engine
from app.observability.boot_guard import (
    BootGuardError,
    database_failures,
    enforce_config,
)


async def boot_worker(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    enforce_config(settings)
    if settings.is_production and settings.is_db_configured:
        async with get_engine().connect() as conn:
            failures = await database_failures(conn, settings)
            if failures:
                raise BootGuardError(failures)
