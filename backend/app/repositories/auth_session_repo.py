"""Auth session repository.

Auth sessions are app-side revocation records only; provider tokens are never
stored. Use an auth-context DB session for pre-tenant revocation lookups.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update

from app.models.auth_session import AuthSession
from app.repositories.base import BaseRepository


class AuthSessionRepository(BaseRepository):
    async def get_by_provider_session_ref(self, provider_session_ref: str) -> Any | None:
        stmt = select(AuthSession).where(AuthSession.provider_session_ref == provider_session_ref)
        return (await self.conn.execute(stmt)).scalars().first()

    async def is_revoked(self, provider_session_ref: str) -> bool:
        row = await self.get_by_provider_session_ref(provider_session_ref)
        return bool(row is not None and row.revoked_at is not None)

    async def upsert_active(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        provider_session_ref: str,
        membership_version: int,
        expires_at: datetime | None,
    ) -> None:
        existing = await self.get_by_provider_session_ref(provider_session_ref)
        if existing is None:
            await self.conn.execute(
                insert(AuthSession).values(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    provider_session_ref=provider_session_ref,
                    membership_version=membership_version,
                    expires_at=expires_at,
                )
            )
            return
        await self.conn.execute(
            update(AuthSession)
            .where(AuthSession.provider_session_ref == provider_session_ref)
            .values(
                user_id=user_id,
                tenant_id=tenant_id,
                membership_version=membership_version,
                expires_at=expires_at,
            )
        )

    async def revoke(self, *, provider_session_ref: str, revoked_at: datetime) -> int:
        result = await self.conn.execute(
            update(AuthSession)
            .where(AuthSession.provider_session_ref == provider_session_ref)
            .values(revoked_at=revoked_at)
        )
        return int(result.rowcount or 0)

    async def revoke_all_for_user(self, *, user_id: uuid.UUID, revoked_at: datetime) -> int:
        result = await self.conn.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        return int(result.rowcount or 0)
