"""User repository (global identity lookups by provider mapping)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_identity(self, identity_provider: str, provider_user_id: str) -> Any:
        stmt = select(User).where(
            User.identity_provider == identity_provider,
            User.provider_user_id == provider_user_id,
        )
        return (await self.conn.execute(stmt)).first()
