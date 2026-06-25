"""Tenant membership repository (tenant-scoped)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.models.membership import TenantMembership
from app.repositories.base import BaseRepository
from app.services.settings_api import MembershipReadRecord


def _membership_record(row: TenantMembership) -> MembershipReadRecord:
    return MembershipReadRecord(
        id=row.id,
        user_id=row.user_id,
        role=row.role,
        membership_version=row.membership_version,
        created_at=row.created_at,
    )


class MembershipRepository(BaseRepository):
    async def list_for_current_tenant(self) -> list[Any]:
        """List memberships for the active tenant (RLS scopes the rows)."""
        return list((await self.conn.execute(select(TenantMembership))).all())

    async def list_memberships(self) -> list[MembershipReadRecord]:
        """List safe membership records for the active tenant."""
        rows = (await self.conn.execute(select(TenantMembership))).scalars().all()
        return [_membership_record(row) for row in rows]

    async def get_for_user_and_tenant(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Any | None:
        """Return a membership for the active tenant; RLS blocks other tenants."""
        stmt = select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
        )
        return (await self.conn.execute(stmt)).scalars().first()
