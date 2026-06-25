"""Tenant repository (tenant-scoped; RLS restricts rows to the active tenant)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository
from app.services.settings_api import TenantSettingsRecord


def _tenant_record(row: Tenant) -> TenantSettingsRecord:
    return TenantSettingsRecord(
        id=row.id,
        name=row.name,
        status=row.status,
        settings=row.settings,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class TenantRepository(BaseRepository):
    async def get_current(self) -> Any:
        """Return the active tenant row (RLS already scopes to it)."""
        return (await self.conn.execute(select(Tenant))).first()

    async def get_current_tenant(self) -> TenantSettingsRecord | None:
        """Return the active tenant as a safe API record."""
        row = (await self.conn.execute(select(Tenant))).scalars().first()
        return _tenant_record(row) if row is not None else None

    async def update_current_tenant(
        self, *, name: str | None = None, settings: dict[str, Any] | None = None
    ) -> TenantSettingsRecord:
        values: dict[str, Any] = {}
        if name is not None:
            values["name"] = name
        if settings is not None:
            values["settings"] = settings
        row = (
            (await self.conn.execute(update(Tenant).values(**values).returning(Tenant)))
            .scalars()
            .one()
        )
        return _tenant_record(row)
