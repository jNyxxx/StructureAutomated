"""Tenant membership repository (tenant-scoped)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.membership import TenantMembership
from app.repositories.base import BaseRepository


class MembershipRepository(BaseRepository):
    async def list_for_current_tenant(self) -> list[Any]:
        """List memberships for the active tenant (RLS scopes the rows)."""
        return list((await self.conn.execute(select(TenantMembership))).all())
