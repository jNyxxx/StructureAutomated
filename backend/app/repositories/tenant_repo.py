"""Tenant repository (tenant-scoped; RLS restricts rows to the active tenant)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository):
    async def get_current(self) -> Any:
        """Return the active tenant row (RLS already scopes to it)."""
        return (await self.conn.execute(select(Tenant))).first()
