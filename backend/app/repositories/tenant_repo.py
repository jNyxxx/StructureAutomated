"""Tenant repository (tenant-scoped; RLS restricts rows to the active tenant)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository
from app.services.settings_api import TenantSettingsRecord

_TENANT_COLUMNS = (
    Tenant.id,
    Tenant.name,
    Tenant.status,
    Tenant.settings,
    Tenant.created_at,
    Tenant.updated_at,
)


def _tenant_record(row: RowMapping) -> TenantSettingsRecord:
    return TenantSettingsRecord(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        settings=row["settings"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class TenantRepository(BaseRepository):
    async def create(self, *, id: uuid.UUID, name: str) -> TenantSettingsRecord:
        """Insert a new tenant row. Caller must check existence first (not idempotent)."""
        row = (
            (
                await self.conn.execute(
                    insert(Tenant).values(id=id, name=name).returning(*_TENANT_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _tenant_record(row)

    async def get_current(self) -> Any:
        """Return the active tenant row (RLS already scopes to it).

        Unused (no callers found repo-wide as of the P4 row-mapping hardening
        audit); returns a raw Row without attribute-safe mapping. Deferred —
        do not rely on attribute access if this is ever wired up.
        """
        return (await self.conn.execute(select(Tenant))).first()

    async def get_current_tenant(self) -> TenantSettingsRecord | None:
        """Return the active tenant as a safe API record."""
        row = (await self.conn.execute(select(*_TENANT_COLUMNS))).mappings().first()
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
            (await self.conn.execute(update(Tenant).values(**values).returning(*_TENANT_COLUMNS)))
            .mappings()
            .one()
        )
        return _tenant_record(row)
