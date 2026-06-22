"""Tenant membership repository (tenant-scoped)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.models.membership import TenantMembership
from app.repositories.base import BaseRepository


class MembershipRepository(BaseRepository):
    async def list_for_current_tenant(self) -> list[Any]:
        """List memberships for the active tenant (RLS scopes the rows)."""
        return list((await self.conn.execute(select(TenantMembership))).all())

    async def get_for_user_and_tenant(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Any | None:
        """Return a membership for the active tenant; RLS blocks other tenants."""
        stmt = select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
        )
        return (await self.conn.execute(stmt)).scalars().first()
