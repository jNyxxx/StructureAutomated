"""RAG knowledge and grounding service for Phase 1 Slice P1-04."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import (
    CAN_MANAGE_KNOWLEDGE,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)
from app.services.billing import CAN_RUN_AGENTS as BILLING_CAN_RUN_AGENTS
from app.services.billing import BillingGateService


@dataclass(frozen=True)
class KnowledgeDocumentRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    source_url: str | None
    content: str
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True)
class KnowledgeChunkRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    created_at: datetime


@dataclass(frozen=True)
class ResearchArtifactRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    research_run_id: uuid.UUID
    contact_id: uuid.UUID
    findings: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class GroundingChunk:
    source_type: str  # "knowledge_chunk" | "research_artifact"
    source_id: uuid.UUID
    content: str
    tenant_id: uuid.UUID
    score: float = 1.0


@dataclass(frozen=True)
class GroundingContextResult:
    chunks: list[GroundingChunk]


class GroundingCampaignStore(Protocol):
    async def get_campaign(self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Any | None:
        """Get campaign details."""


class GroundingContactStore(Protocol):
    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        """Get contact details."""


class ComplianceGate(Protocol):
    async def is_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> bool:
        """Check if suppressed."""


class KnowledgeStore(Protocol):
    async def create_document(
        self,
        *,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        source_url: str | None = None,
        status: str = "active",
    ) -> KnowledgeDocumentRecord:
        """Create a knowledge document."""

    async def get_document(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> KnowledgeDocumentRecord | None:
        """Get a knowledge document."""

    async def get_chunk(
        self, *, tenant_id: uuid.UUID, chunk_id: uuid.UUID
    ) -> KnowledgeChunkRecord | None:
        """Get a knowledge chunk."""

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
        """Update a knowledge document."""

    async def create_chunks(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: list[str],
    ) -> list[KnowledgeChunkRecord]:
        """Create knowledge chunks."""

    async def delete_chunks(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        """Delete chunks for a document."""

    async def list_chunks_for_grounding(
        self, *, tenant_id: uuid.UUID
    ) -> list[KnowledgeChunkRecord]:
        """List active grounding chunks."""

    async def get_research_artifact_for_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ResearchArtifactRecord | None:
        """Get contact latest research artifact."""


AuditRecorder = Any


def _obj(record: Any | None) -> TenantOwnedObject | None:
    if record is None:
        return None
    return TenantOwnedObject(id=record.id, tenant_id=record.tenant_id)


def chunk_text(text_content: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Safe character-based text chunking with overlap."""
    cleaned = text_content.strip()
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        start += chunk_size - overlap
        if start >= len(cleaned) or chunk_size <= overlap:
            break
    return chunks


class RAGGroundingService:
    """RAG grounding context preparation and document chunking service."""

    def __init__(
        self,
        *,
        knowledge_store: KnowledgeStore,
        campaign_store: GroundingCampaignStore,
        contact_store: GroundingContactStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
        billing: BillingGateService,
        compliance: ComplianceGate | None = None,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._knowledge_store = knowledge_store
        self._campaign_store = campaign_store
        self._contact_store = contact_store
        self._rbac = rbac
        self._object_authz = object_authz
        self._billing = billing
        self._compliance = compliance
        self._audit_record = audit_record

    async def add_document(
        self,
        *,
        principal: CurrentPrincipal,
        title: str,
        content: str,
        source_url: str | None = None,
        chunk_size: int = 500,
        overlap: int = 50,
        now: datetime,
    ) -> KnowledgeDocumentRecord:
        # 1. RBAC Check
        self._rbac.require(principal, CAN_MANAGE_KNOWLEDGE)

        cleaned_title = title.strip()
        cleaned_content = content.strip()
        if not cleaned_title or not cleaned_content:
            raise AppError("INVALID_DOCUMENT", "Title and content are required.", status_code=400)

        # 2. Create document record
        doc = await self._knowledge_store.create_document(
            tenant_id=principal.tenant_id,
            title=cleaned_title,
            content=cleaned_content,
            source_url=source_url,
            status="active",
        )

        # 3. Audit created event
        await self._audit(
            event_type="knowledge.document_created",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="knowledge_document",
            object_id=doc.id,
            details={"title": cleaned_title},
        )

        # 4. Chunk document text
        chunks = chunk_text(cleaned_content, chunk_size=chunk_size, overlap=overlap)
        if chunks:
            await self._knowledge_store.create_chunks(
                tenant_id=principal.tenant_id,
                document_id=doc.id,
                chunks=chunks,
            )

        # 5. Audit chunked event
        await self._audit(
            event_type="knowledge.document_chunked",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="knowledge_document",
            object_id=doc.id,
            details={"chunks_count": len(chunks)},
        )

        return doc

    async def delete_document(
        self,
        *,
        principal: CurrentPrincipal,
        document_id: uuid.UUID,
        now: datetime,
    ) -> KnowledgeDocumentRecord:
        # 1. RBAC Check
        self._rbac.require(principal, CAN_MANAGE_KNOWLEDGE)

        # 2. Fetch doc & object auth
        doc = await self._knowledge_store.get_document(
            tenant_id=principal.tenant_id, document_id=document_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(doc))
        if doc is None:
            raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status_code=404)

        # 3. Soft-delete document
        updated = await self._knowledge_store.update_document(
            tenant_id=principal.tenant_id,
            document_id=document_id,
            status="deleted",
            deleted_at=now,
        )

        # 4. Delete associated chunks
        await self._knowledge_store.delete_chunks(
            tenant_id=principal.tenant_id, document_id=document_id
        )

        # 5. Audit deleted event
        await self._audit(
            event_type="knowledge.document_deleted",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="knowledge_document",
            object_id=document_id,
            details={"title": doc.title},
        )

        if updated is None:
            raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status_code=404)
        return updated

    async def retrieve_grounding_context(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        query: str | None = None,
        now: datetime | None = None,
    ) -> GroundingContextResult:
        # 1. Billing check
        current_now = now or datetime.now(UTC)
        await self._billing.require_feature(
            principal.tenant_id, BILLING_CAN_RUN_AGENTS, now=current_now
        )

        # 2. Fetch Campaign and verify ownership
        campaign = await self._campaign_store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(campaign))
        if campaign is None:
            raise AppError("CAMPAIGN_NOT_FOUND", "Campaign not found.", status_code=404)

        # 2. Fetch Contact and verify ownership
        contact = await self._contact_store.get_contact(
            tenant_id=principal.tenant_id, contact_id=contact_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(contact))
        if contact is None:
            raise AppError("CONTACT_NOT_FOUND", "Contact not found.", status_code=404)

        # 3. Compliance and Suppression check
        if self._compliance is not None and contact.email:
            is_suppressed = await self._compliance.is_suppressed(
                tenant_id=principal.tenant_id, channel="email", contact_identifier=contact.email
            )
            if is_suppressed:
                raise AppError(
                    "CONTACT_SUPPRESSED",
                    "Cannot retrieve grounding context for a suppressed contact.",
                    status_code=403,
                )

        chunks: list[GroundingChunk] = []

        # 4. Fetch Research Artifact findings
        artifact = await self._knowledge_store.get_research_artifact_for_contact(
            tenant_id=principal.tenant_id, contact_id=contact_id
        )
        if artifact is not None:
            formatted_findings = (
                f"Research Findings for contact {contact.full_name or contact.email}: "
                f"{artifact.findings}"
            )
            chunks.append(
                GroundingChunk(
                    source_type="research_artifact",
                    source_id=artifact.id,
                    content=formatted_findings,
                    tenant_id=artifact.tenant_id,
                    score=1.0,
                )
            )

        # 5. Fetch Active Chunks for grounding
        active_chunks = await self._knowledge_store.list_chunks_for_grounding(
            tenant_id=principal.tenant_id
        )

        # Filter chunks by query lexical matching if query is specified
        if query:
            cleaned_query = query.strip().lower()
            matched_chunks = [c for c in active_chunks if cleaned_query in c.content.lower()]
            for c in matched_chunks:
                chunks.append(
                    GroundingChunk(
                        source_type="knowledge_chunk",
                        source_id=c.id,
                        content=c.content,
                        tenant_id=c.tenant_id,
                        score=1.0,
                    )
                )
        else:
            # Return first few chunks (limit 3) if no query is specified
            for c in active_chunks[:3]:
                chunks.append(
                    GroundingChunk(
                        source_type="knowledge_chunk",
                        source_id=c.id,
                        content=c.content,
                        tenant_id=c.tenant_id,
                        score=1.0,
                    )
                )

        return GroundingContextResult(chunks=chunks)

    async def _audit(
        self,
        *,
        event_type: str,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        object_type: str,
        object_id: uuid.UUID,
        details: dict[str, Any],
    ) -> None:
        if self._audit_record is not None:
            if callable(self._audit_record):
                await self._audit_record(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    object_type=object_type,
                    object_id=object_id,
                    details=details,
                )
            else:
                await self._audit_record.record(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    object_type=object_type,
                    object_id=object_id,
                    details=details,
                )
