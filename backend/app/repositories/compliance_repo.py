"""Compliance profile and suppression repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, insert, or_, select, update

from app.models.compliance import ComplianceProfile, Suppression
from app.repositories.base import BaseRepository
from app.services.compliance import ComplianceProfileRecord, SuppressionRecord


def _profile(row: ComplianceProfile) -> ComplianceProfileRecord:
    return ComplianceProfileRecord(
        tenant_id=row.tenant_id,
        jurisdiction=row.jurisdiction,
        sending_review_required=row.sending_review_required,
        live_sending_allowed=row.live_sending_allowed,
        sms_allowed=row.sms_allowed,
    )


def _suppression(row: Suppression) -> SuppressionRecord:
    return SuppressionRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        channel=row.channel,
        contact_hash=row.contact_hash,
        reason=row.reason,
        source=row.source,
        never_contact=row.never_contact,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


class ComplianceRepository(BaseRepository):
    async def get_profile(self, tenant_id: uuid.UUID) -> ComplianceProfileRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(ComplianceProfile).where(ComplianceProfile.tenant_id == tenant_id)
                )
            )
            .scalars()
            .first()
        )
        return _profile(row) if row is not None else None

    async def upsert_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        jurisdiction: str,
        sending_review_required: bool,
        live_sending_allowed: bool,
        sms_allowed: bool,
    ) -> ComplianceProfileRecord:
        existing = await self.get_profile(tenant_id)
        if existing is None:
            row = (
                (
                    await self.conn.execute(
                        insert(ComplianceProfile)
                        .values(
                            tenant_id=tenant_id,
                            jurisdiction=jurisdiction,
                            sending_review_required=sending_review_required,
                            live_sending_allowed=live_sending_allowed,
                            sms_allowed=sms_allowed,
                        )
                        .returning(ComplianceProfile)
                    )
                )
                .scalars()
                .one()
            )
            return _profile(row)
        row = (
            (
                await self.conn.execute(
                    update(ComplianceProfile)
                    .where(ComplianceProfile.tenant_id == tenant_id)
                    .values(
                        jurisdiction=jurisdiction,
                        sending_review_required=sending_review_required,
                        live_sending_allowed=live_sending_allowed,
                        sms_allowed=sms_allowed,
                    )
                    .returning(ComplianceProfile)
                )
            )
            .scalars()
            .one()
        )
        return _profile(row)

    async def get_active_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
    ) -> SuppressionRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(Suppression).where(
                        Suppression.tenant_id == tenant_id,
                        Suppression.channel == channel,
                        Suppression.contact_hash == contact_hash,
                        Suppression.revoked_at.is_(None),
                    )
                )
            )
            .scalars()
            .first()
        )
        return _suppression(row) if row is not None else None

    async def get_suppression(
        self, *, tenant_id: uuid.UUID, suppression_id: uuid.UUID
    ) -> SuppressionRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(Suppression).where(
                        Suppression.tenant_id == tenant_id,
                        Suppression.id == suppression_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _suppression(row) if row is not None else None

    async def list_suppressions(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[SuppressionRecord], str | None]:
        stmt = select(Suppression).where(Suppression.tenant_id == tenant_id)
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                return [], None
            cursor_row = (
                (
                    await self.conn.execute(
                        select(Suppression).where(
                            Suppression.tenant_id == tenant_id,
                            Suppression.id == cursor_id,
                        )
                    )
                )
                .scalars()
                .first()
            )
            if cursor_row is None:
                return [], None
            stmt = stmt.where(
                or_(
                    Suppression.created_at < cursor_row.created_at,
                    and_(
                        Suppression.created_at == cursor_row.created_at,
                        Suppression.id < cursor_row.id,
                    ),
                )
            )

        rows = (
            (
                await self.conn.execute(
                    stmt.order_by(Suppression.created_at.desc(), Suppression.id.desc()).limit(
                        limit + 1
                    )
                )
            )
            .scalars()
            .all()
        )
        page_rows = rows[:limit]
        next_cursor = str(page_rows[-1].id) if len(rows) > limit and page_rows else None
        return [_suppression(row) for row in page_rows], next_cursor

    async def add_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
        reason: str,
        source: str,
        never_contact: bool,
        created_at: datetime,
    ) -> SuppressionRecord:
        row = (
            (
                await self.conn.execute(
                    insert(Suppression)
                    .values(
                        tenant_id=tenant_id,
                        channel=channel,
                        contact_hash=contact_hash,
                        reason=reason,
                        source=source,
                        never_contact=never_contact,
                        created_at=created_at,
                    )
                    .returning(Suppression)
                )
            )
            .scalars()
            .one()
        )
        return _suppression(row)

    async def revoke_suppression(
        self,
        *,
        suppression_id: uuid.UUID,
        revoked_at: datetime,
    ) -> SuppressionRecord | None:
        row = (
            (
                await self.conn.execute(
                    update(Suppression)
                    .where(Suppression.id == suppression_id)
                    .values(revoked_at=revoked_at)
                    .returning(Suppression)
                )
            )
            .scalars()
            .first()
        )
        return _suppression(row) if row is not None else None
