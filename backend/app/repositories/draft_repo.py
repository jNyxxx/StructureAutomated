"""Repository for drafts and draft evidence storage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import insert, select, update

from app.models.draft import Draft, DraftEvidence
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class DraftRecord:
    """Read-only representation of a Draft."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str
    subject: str
    body: str
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DraftEvidenceRecord:
    """Read-only representation of DraftEvidence."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    draft_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    content_snippet: str
    created_at: datetime


def _draft(row: Draft) -> DraftRecord:
    return DraftRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        campaign_id=row.campaign_id,
        contact_id=row.contact_id,
        status=row.status,
        subject=row.subject,
        body=row.body,
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _evidence(row: DraftEvidence) -> DraftEvidenceRecord:
    return DraftEvidenceRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        draft_id=row.draft_id,
        source_type=row.source_type,
        source_id=row.source_id,
        content_snippet=row.content_snippet,
        created_at=row.created_at,
    )


class DraftRepository(BaseRepository):
    """Tenant-scoped repository for drafts and evidence."""

    async def create_draft(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
        subject: str,
        body: str,
        idempotency_key: str | None = None,
    ) -> DraftRecord:
        row = (
            (
                await self.conn.execute(
                    insert(Draft)
                    .values(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        contact_id=contact_id,
                        status=status,
                        subject=subject,
                        body=body,
                        idempotency_key=idempotency_key,
                    )
                    .returning(Draft)
                )
            )
            .scalars()
            .one()
        )
        return _draft(row)

    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> DraftRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(Draft).where(
                        Draft.tenant_id == tenant_id,
                        Draft.id == draft_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _draft(row) if row is not None else None

    async def get_draft_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, key: str
    ) -> DraftRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(Draft).where(
                        Draft.tenant_id == tenant_id,
                        Draft.idempotency_key == key,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _draft(row) if row is not None else None

    async def create_evidence(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        content_snippet: str,
    ) -> DraftEvidenceRecord:
        row = (
            (
                await self.conn.execute(
                    insert(DraftEvidence)
                    .values(
                        tenant_id=tenant_id,
                        draft_id=draft_id,
                        source_type=source_type,
                        source_id=source_id,
                        content_snippet=content_snippet,
                    )
                    .returning(DraftEvidence)
                )
            )
            .scalars()
            .one()
        )
        return _evidence(row)

    async def list_evidence_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> list[DraftEvidenceRecord]:
        rows = (
            (
                await self.conn.execute(
                    select(DraftEvidence).where(
                        DraftEvidence.tenant_id == tenant_id,
                        DraftEvidence.draft_id == draft_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return [_evidence(r) for r in rows]

    async def update_draft_status(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID, status: str
    ) -> DraftRecord | None:
        row = (
            (
                await self.conn.execute(
                    update(Draft)
                    .where(Draft.tenant_id == tenant_id, Draft.id == draft_id)
                    .values(status=status)
                    .returning(Draft)
                )
            )
            .scalars()
            .first()
        )
        return _draft(row) if row is not None else None
