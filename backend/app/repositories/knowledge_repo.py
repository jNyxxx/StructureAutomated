"""Repository for knowledge documents, chunks, and RAG grounding."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, insert, select, update

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.research import ResearchArtifact
from app.repositories.base import BaseRepository
from app.services.rag_grounding import (
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    ResearchArtifactRecord,
)


def _document(row: KnowledgeDocument) -> KnowledgeDocumentRecord:
    return KnowledgeDocumentRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        source_url=row.source_url,
        content=row.content,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def _chunk(row: KnowledgeChunk) -> KnowledgeChunkRecord:
    return KnowledgeChunkRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        document_id=row.document_id,
        chunk_index=row.chunk_index,
        content=row.content,
        created_at=row.created_at,
    )


def _research_artifact(row: ResearchArtifact) -> ResearchArtifactRecord:
    return ResearchArtifactRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        research_run_id=row.research_run_id,
        contact_id=row.contact_id,
        findings=row.findings,
        created_at=row.created_at,
    )


class KnowledgeRepository(BaseRepository):
    async def create_document(
        self,
        *,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        source_url: str | None = None,
        status: str = "active",
    ) -> KnowledgeDocumentRecord:
        row = (
            (
                await self.conn.execute(
                    insert(KnowledgeDocument)
                    .values(
                        tenant_id=tenant_id,
                        title=title,
                        content=content,
                        source_url=source_url,
                        status=status,
                    )
                    .returning(KnowledgeDocument)
                )
            )
            .scalars()
            .one()
        )
        return _document(row)

    async def get_document(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> KnowledgeDocumentRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.tenant_id == tenant_id,
                        KnowledgeDocument.id == document_id,
                        KnowledgeDocument.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .first()
        )
        return _document(row) if row is not None else None

    async def get_chunk(
        self, *, tenant_id: uuid.UUID, chunk_id: uuid.UUID
    ) -> KnowledgeChunkRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(KnowledgeChunk).where(
                        KnowledgeChunk.tenant_id == tenant_id,
                        KnowledgeChunk.id == chunk_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _chunk(row) if row is not None else None

    async def update_document(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        title: str | None = None,
        content: str | None = None,
        source_url: str | None = None,
        status: str | None = None,
        deleted_at: Any = None,
    ) -> KnowledgeDocumentRecord | None:
        values: dict[str, Any] = {}
        if title is not None:
            values["title"] = title
        if content is not None:
            values["content"] = content
        if source_url is not None:
            values["source_url"] = source_url
        if status is not None:
            values["status"] = status
        if deleted_at is not None:
            values["deleted_at"] = deleted_at

        if not values:
            return await self.get_document(tenant_id=tenant_id, document_id=document_id)

        row = (
            (
                await self.conn.execute(
                    update(KnowledgeDocument)
                    .where(
                        KnowledgeDocument.tenant_id == tenant_id,
                        KnowledgeDocument.id == document_id,
                    )
                    .values(**values)
                    .returning(KnowledgeDocument)
                )
            )
            .scalars()
            .first()
        )
        return _document(row) if row is not None else None

    async def create_chunks(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: list[str],
    ) -> list[KnowledgeChunkRecord]:
        inserted: list[KnowledgeChunkRecord] = []
        for i, text_content in enumerate(chunks):
            row = (
                (
                    await self.conn.execute(
                        insert(KnowledgeChunk)
                        .values(
                            tenant_id=tenant_id,
                            document_id=document_id,
                            chunk_index=i,
                            content=text_content,
                        )
                        .returning(KnowledgeChunk)
                    )
                )
                .scalars()
                .one()
            )
            inserted.append(_chunk(row))
        return inserted

    async def delete_chunks(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        await self.conn.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.tenant_id == tenant_id,
                KnowledgeChunk.document_id == document_id,
            )
        )

    async def list_chunks_for_grounding(
        self, *, tenant_id: uuid.UUID
    ) -> list[KnowledgeChunkRecord]:
        # Retrieve active chunks (status='active' and not deleted)
        rows = (
            (
                await self.conn.execute(
                    select(KnowledgeChunk)
                    .join(KnowledgeDocument)
                    .where(
                        KnowledgeChunk.tenant_id == tenant_id,
                        KnowledgeDocument.status == "active",
                        KnowledgeDocument.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        return [_chunk(r) for r in rows]

    async def get_research_artifact_for_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ResearchArtifactRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(ResearchArtifact)
                    .where(
                        ResearchArtifact.tenant_id == tenant_id,
                        ResearchArtifact.contact_id == contact_id,
                    )
                    .order_by(ResearchArtifact.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        return _research_artifact(row) if row is not None else None
