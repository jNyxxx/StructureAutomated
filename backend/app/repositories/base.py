"""Repository base.

Repositories perform tenant-scoped SQL only and must be given a connection from
``app.database.tenant_session`` (which has set the transaction-local tenant
context). They never open their own engine/connection (CLAUDE.md rule 5).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection


class BaseRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    @property
    def conn(self) -> AsyncConnection:
        return self._conn
