"""Support-access repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping

from app.models.support_access import SupportAccessGrantModel
from app.repositories.base import BaseRepository
from app.services.authz import SupportAccessGrant

_SUPPORT_ACCESS_GRANT_COLUMNS = (
    SupportAccessGrantModel.id,
    SupportAccessGrantModel.tenant_id,
    SupportAccessGrantModel.support_user_id,
    SupportAccessGrantModel.granted_by_user_id,
    SupportAccessGrantModel.reason,
    SupportAccessGrantModel.scope,
    SupportAccessGrantModel.expires_at,
    SupportAccessGrantModel.revoked_at,
    SupportAccessGrantModel.created_at,
)


def _to_grant(row: RowMapping) -> SupportAccessGrant:
    return SupportAccessGrant(
        id=row["id"],
        tenant_id=row["tenant_id"],
        support_user_id=row["support_user_id"],
        granted_by_user_id=row["granted_by_user_id"],
        reason=row["reason"],
        scope=row["scope"],
        expires_at=row["expires_at"],
        revoked_at=row["revoked_at"],
        created_at=row["created_at"],
    )


class SupportAccessRepository(BaseRepository):
    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        support_user_id: uuid.UUID,
        granted_by_user_id: uuid.UUID,
        reason: str,
        scope: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> SupportAccessGrant:
        stmt = (
            insert(SupportAccessGrantModel)
            .values(
                tenant_id=tenant_id,
                support_user_id=support_user_id,
                granted_by_user_id=granted_by_user_id,
                reason=reason,
                scope=scope,
                expires_at=expires_at,
                created_at=created_at,
            )
            .returning(*_SUPPORT_ACCESS_GRANT_COLUMNS)
        )
        row = (await self.conn.execute(stmt)).mappings().one()
        return _to_grant(row)

    async def get_active(
        self,
        *,
        tenant_id: uuid.UUID,
        support_user_id: uuid.UUID,
        scope: str,
        now: datetime,
    ) -> SupportAccessGrant | None:
        stmt = select(*_SUPPORT_ACCESS_GRANT_COLUMNS).where(
            SupportAccessGrantModel.tenant_id == tenant_id,
            SupportAccessGrantModel.support_user_id == support_user_id,
            SupportAccessGrantModel.scope == scope,
            SupportAccessGrantModel.revoked_at.is_(None),
            SupportAccessGrantModel.expires_at > now,
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        return _to_grant(row) if row is not None else None

    async def revoke(
        self,
        *,
        grant_id: uuid.UUID,
        revoked_at: datetime,
    ) -> SupportAccessGrant | None:
        stmt = (
            update(SupportAccessGrantModel)
            .where(SupportAccessGrantModel.id == grant_id)
            .values(revoked_at=revoked_at)
            .returning(*_SUPPORT_ACCESS_GRANT_COLUMNS)
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        return _to_grant(row) if row is not None else None
