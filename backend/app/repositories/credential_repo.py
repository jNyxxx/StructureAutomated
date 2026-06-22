"""Integration-credential repository (tenant-scoped; stores ref + metadata only)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import insert, select

from app.models.integration_credential import IntegrationCredential
from app.repositories.base import BaseRepository


class CredentialRepository(BaseRepository):
    async def insert(self, payload: dict[str, Any]) -> None:
        await self.conn.execute(insert(IntegrationCredential).values(**payload))

    async def get_by_type(self, credential_type: str) -> Any:
        stmt = select(IntegrationCredential).where(
            IntegrationCredential.credential_type == credential_type
        )
        return (await self.conn.execute(stmt)).first()
