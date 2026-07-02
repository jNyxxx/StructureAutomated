"""User repository (global identity lookups by provider mapping)."""

from __future__ import annotations

import uuid

from sqlalchemy import insert, select
from sqlalchemy.engine import RowMapping

from app.models.user import User
from app.repositories.base import BaseRepository
from app.services.auth import AuthUser

_AUTH_USER_COLUMNS = (
    User.id,
    User.email,
    User.identity_provider,
    User.provider_user_id,
    User.deleted_at,
)


def _auth_user(row: RowMapping) -> AuthUser:
    return AuthUser(
        id=row["id"],
        email=row["email"],
        identity_provider=row["identity_provider"],
        provider_user_id=row["provider_user_id"],
        deleted_at=row["deleted_at"],
    )


class UserRepository(BaseRepository):
    async def create(
        self, *, id: uuid.UUID, email: str, identity_provider: str, provider_user_id: str
    ) -> AuthUser:
        """Insert a new user row. Caller must check existence first (not idempotent)."""
        row = (
            (
                await self.conn.execute(
                    insert(User)
                    .values(
                        id=id,
                        email=email,
                        identity_provider=identity_provider,
                        provider_user_id=provider_user_id,
                    )
                    .returning(*_AUTH_USER_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _auth_user(row)

    async def get_by_identity(
        self, *, identity_provider: str, provider_user_id: str
    ) -> AuthUser | None:
        stmt = select(*_AUTH_USER_COLUMNS).where(
            User.identity_provider == identity_provider,
            User.provider_user_id == provider_user_id,
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        return _auth_user(row) if row is not None else None
