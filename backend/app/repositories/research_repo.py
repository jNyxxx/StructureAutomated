"""Repository for research runs and artifacts."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping

from app.models.contact import Contact
from app.models.research import ResearchArtifact, ResearchRun
from app.repositories.base import BaseRepository
from app.services.csv_import import ContactRecord

if TYPE_CHECKING:
    from app.services.research import ResearchArtifactRecord, ResearchRunRecord

_RESEARCH_RUN_COLUMNS = (
    ResearchRun.id,
    ResearchRun.tenant_id,
    ResearchRun.campaign_id,
    ResearchRun.created_by_user_id,
    ResearchRun.status,
    ResearchRun.queued_count,
    ResearchRun.processed_count,
    ResearchRun.failed_count,
    ResearchRun.created_at,
    ResearchRun.updated_at,
)
_RESEARCH_ARTIFACT_COLUMNS = (
    ResearchArtifact.id,
    ResearchArtifact.tenant_id,
    ResearchArtifact.research_run_id,
    ResearchArtifact.contact_id,
    ResearchArtifact.findings,
    ResearchArtifact.created_at,
)
_RESEARCH_CONTACT_COLUMNS = (
    Contact.id,
    Contact.tenant_id,
    Contact.dedupe_hash,
    Contact.normalized_email,
    Contact.normalized_domain,
    Contact.normalized_company,
    Contact.full_name,
    Contact.title,
    Contact.email,
    Contact.domain,
    Contact.company_name,
)


def _research_run(row: RowMapping) -> ResearchRunRecord:
    from app.services.research import ResearchRunRecord

    return ResearchRunRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        campaign_id=row["campaign_id"],
        created_by_user_id=row["created_by_user_id"],
        status=row["status"],
        queued_count=row["queued_count"],
        processed_count=row["processed_count"],
        failed_count=row["failed_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _research_artifact(row: RowMapping) -> ResearchArtifactRecord:
    from app.services.research import ResearchArtifactRecord

    return ResearchArtifactRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        research_run_id=row["research_run_id"],
        contact_id=row["contact_id"],
        findings=row["findings"],
        created_at=row["created_at"],
    )


def _research_contact(row: RowMapping) -> ContactRecord:
    return ContactRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        dedupe_hash=row["dedupe_hash"],
        normalized_email=row["normalized_email"],
        normalized_domain=row["normalized_domain"],
        normalized_company=row["normalized_company"],
        full_name=row["full_name"],
        title=row["title"],
        email=row["email"],
        domain=row["domain"],
        company_name=row["company_name"],
    )


class ResearchRepository(BaseRepository):
    async def create_run(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None,
        status: str,
        queued_count: int,
    ) -> ResearchRunRecord:
        row = (
            (
                await self.conn.execute(
                    insert(ResearchRun)
                    .values(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        created_by_user_id=created_by_user_id,
                        status=status,
                        queued_count=queued_count,
                    )
                    .returning(*_RESEARCH_RUN_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _research_run(row)

    async def get_run(self, *, tenant_id: uuid.UUID, run_id: uuid.UUID) -> ResearchRunRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_RESEARCH_RUN_COLUMNS).where(
                        ResearchRun.tenant_id == tenant_id, ResearchRun.id == run_id
                    )
                )
            )
            .mappings()
            .first()
        )
        return _research_run(row) if row is not None else None

    async def update_run(
        self,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        status: str | None = None,
        processed_count: int | None = None,
        failed_count: int | None = None,
    ) -> ResearchRunRecord | None:
        values: dict[str, Any] = {}
        if status is not None:
            values["status"] = status
        if processed_count is not None:
            values["processed_count"] = processed_count
        if failed_count is not None:
            values["failed_count"] = failed_count

        if not values:
            return await self.get_run(tenant_id=tenant_id, run_id=run_id)

        row = (
            (
                await self.conn.execute(
                    update(ResearchRun)
                    .where(ResearchRun.tenant_id == tenant_id, ResearchRun.id == run_id)
                    .values(**values)
                    .returning(*_RESEARCH_RUN_COLUMNS)
                )
            )
            .mappings()
            .first()
        )
        return _research_run(row) if row is not None else None

    async def increment_run_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        processed: int = 0,
        failed: int = 0,
    ) -> ResearchRunRecord | None:
        row = (
            (
                await self.conn.execute(
                    update(ResearchRun)
                    .where(ResearchRun.tenant_id == tenant_id, ResearchRun.id == run_id)
                    .values(
                        processed_count=ResearchRun.processed_count + processed,
                        failed_count=ResearchRun.failed_count + failed,
                    )
                    .returning(*_RESEARCH_RUN_COLUMNS)
                )
            )
            .mappings()
            .first()
        )
        return _research_run(row) if row is not None else None

    async def create_artifact(
        self,
        *,
        tenant_id: uuid.UUID,
        research_run_id: uuid.UUID,
        contact_id: uuid.UUID,
        findings: dict[str, Any],
    ) -> ResearchArtifactRecord:
        row = (
            (
                await self.conn.execute(
                    insert(ResearchArtifact)
                    .values(
                        tenant_id=tenant_id,
                        research_run_id=research_run_id,
                        contact_id=contact_id,
                        findings=findings,
                    )
                    .returning(*_RESEARCH_ARTIFACT_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _research_artifact(row)

    async def get_artifact(
        self, *, tenant_id: uuid.UUID, artifact_id: uuid.UUID
    ) -> ResearchArtifactRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_RESEARCH_ARTIFACT_COLUMNS).where(
                        ResearchArtifact.tenant_id == tenant_id, ResearchArtifact.id == artifact_id
                    )
                )
            )
            .mappings()
            .first()
        )
        return _research_artifact(row) if row is not None else None

    async def list_artifacts(
        self, *, tenant_id: uuid.UUID, research_run_id: uuid.UUID
    ) -> list[ResearchArtifactRecord]:
        rows = (
            (
                await self.conn.execute(
                    select(*_RESEARCH_ARTIFACT_COLUMNS).where(
                        ResearchArtifact.tenant_id == tenant_id,
                        ResearchArtifact.research_run_id == research_run_id,
                    )
                )
            )
            .mappings()
            .all()
        )
        return [_research_artifact(r) for r in rows]

    async def get_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ContactRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_RESEARCH_CONTACT_COLUMNS).where(
                        Contact.tenant_id == tenant_id, Contact.id == contact_id
                    )
                )
            )
            .mappings()
            .first()
        )
        return _research_contact(row) if row is not None else None
