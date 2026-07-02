"""Tenant membership repository (tenant-scoped)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.engine import RowMapping

from app.models.membership import TenantMembership
from app.models.tenant import Tenant
from app.repositories.base import BaseRepository
from app.services.auth import AuthMembership
from app.services.settings_api import MembershipReadRecord

_MEMBERSHIP_COLUMNS = (
    TenantMembership.id,
    TenantMembership.user_id,
    TenantMembership.role,
    TenantMembership.membership_version,
    TenantMembership.created_at,
)
_AUTH_MEMBERSHIP_COLUMNS = (
    TenantMembership.tenant_id,
    TenantMembership.user_id,
    TenantMembership.role,
    TenantMembership.membership_version,
    Tenant.status.label("tenant_status"),
)


def _membership_record(row: RowMapping) -> MembershipReadRecord:
    return MembershipReadRecord(
        id=row["id"],
        user_id=row["user_id"],
        role=row["role"],
        membership_version=row["membership_version"],
        created_at=row["created_at"],
    )


def _auth_membership(row: RowMapping) -> AuthMembership:
    return AuthMembership(
        tenant_id=row["tenant_id"],
        user_id=row["user_id"],
        role=row["role"],
        membership_version=row["membership_version"],
        tenant_status=row["tenant_status"],
    )


class MembershipRepository(BaseRepository):
    async def create(
        self, *, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> MembershipReadRecord:
        """Insert a new membership row. Caller must check existence first (not idempotent)."""
        row = (
            (
                await self.conn.execute(
                    insert(TenantMembership)
                    .values(tenant_id=tenant_id, user_id=user_id, role=role)
                    .returning(*_MEMBERSHIP_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _membership_record(row)

    async def list_for_current_tenant(self) -> list[Any]:
        """List memberships for the active tenant (RLS scopes the rows).

        Unused (no callers found repo-wide as of the P4 row-mapping hardening
        audit); returns raw Row objects without attribute-safe mapping.
        Deferred — do not rely on attribute access if this is ever wired up.
        """
        return list((await self.conn.execute(select(TenantMembership))).all())

    async def list_memberships(self) -> list[MembershipReadRecord]:
        """List safe membership records for the active tenant."""
        rows = (await self.conn.execute(select(*_MEMBERSHIP_COLUMNS))).mappings().all()
        return [_membership_record(row) for row in rows]

    async def get_for_user_and_tenant(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> AuthMembership | None:
        """Return a membership for the active tenant; RLS blocks other tenants."""
        stmt = (
            select(*_AUTH_MEMBERSHIP_COLUMNS)
            .join(Tenant, TenantMembership.tenant_id == Tenant.id)
            .where(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        return _auth_membership(row) if row is not None else None
