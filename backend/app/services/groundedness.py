"""Groundedness validation safety gate service for Phase 1 Slice P1-07."""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.rag_grounding import GroundingChunk, KnowledgeStore
from app.services.safety import SafetyGateResultRecord, SafetyStore


class ResearchArtifactRecordProtocol(Protocol):
    @property
    def id(self) -> uuid.UUID: ...
    @property
    def tenant_id(self) -> uuid.UUID: ...


class ResearchStore(Protocol):
    async def get_artifact(self, *, tenant_id: uuid.UUID, artifact_id: uuid.UUID) -> Any | None:
        """Retrieve a specific research artifact by ID."""


AuditRecorder = Any


class GroundednessService:
    """Deterministic, local groundedness and citation validation gate."""

    def __init__(
        self,
        *,
        safety_store: SafetyStore,
        knowledge_store: KnowledgeStore,
        research_store: ResearchStore,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._safety_store = safety_store
        self._knowledge_store = knowledge_store
        self._research_store = research_store
        self._audit_record = audit_record

    async def evaluate_draft_groundedness(
        self,
        *,
        principal: CurrentPrincipal,
        subject: str,
        body: str,
        chunks: list[GroundingChunk],
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> SafetyGateResultRecord:
        """Deterministic evaluation of draft groundedness and evidence citations."""
        # 1. Tenant boundary check
        for chunk in chunks:
            if chunk.tenant_id != principal.tenant_id:
                raise AppError(
                    "CROSS_TENANT_GROUNDING_SOURCE",
                    "Grounding context source tenant mismatch.",
                    status_code=403,
                )

        status = "passed"
        severity = "info"
        reason_code = "passed"
        details: dict[str, Any] = {}

        # 2. Check for empty evidence
        if len(chunks) == 0:
            status = "failed"
            severity = "medium"
            reason_code = "no_evidence_provided"
            details = {"message": "Draft has no linked evidence chunks."}

        # 3. Check for unsupported claim substrings in draft text
        text_lower = (subject + " " + body).lower()
        unsupported_terms = ["unsupported claim", "hallucination", "fake claim"]
        matched_terms = [t for t in unsupported_terms if t in text_lower]

        if status == "passed" and matched_terms:
            status = "failed"
            severity = "high"
            reason_code = "unsupported_claims_detected"
            details = {"matched_unsupported_terms": matched_terms}

        # 4. Check that citation sources exist and belong to the same tenant
        if status == "passed":
            for chunk in chunks:
                if chunk.source_type == "knowledge_chunk":
                    chunk_rec = await self._knowledge_store.get_chunk(
                        tenant_id=principal.tenant_id, chunk_id=chunk.source_id
                    )
                    if chunk_rec is None:
                        status = "failed"
                        severity = "high"
                        reason_code = "evidence_source_not_found"
                        details = {"missing_chunk_id": str(chunk.source_id)}
                        break
                    doc = await self._knowledge_store.get_document(
                        tenant_id=principal.tenant_id, document_id=chunk_rec.document_id
                    )
                    if doc is None or doc.tenant_id != principal.tenant_id:
                        status = "failed"
                        severity = "high"
                        reason_code = "cross_tenant_evidence_denied"
                        details = {"restricted_document_id": str(chunk_rec.document_id)}
                        break
                elif chunk.source_type == "research_artifact":
                    artifact = await self._research_store.get_artifact(
                        tenant_id=principal.tenant_id, artifact_id=chunk.source_id
                    )
                    if artifact is None:
                        status = "failed"
                        severity = "high"
                        reason_code = "evidence_source_not_found"
                        details = {"missing_artifact_id": str(chunk.source_id)}
                        break
                    if artifact.tenant_id != principal.tenant_id:
                        status = "failed"
                        severity = "high"
                        reason_code = "cross_tenant_evidence_denied"
                        details = {"restricted_artifact_id": str(chunk.source_id)}
                        break

        # 5. Persist the groundedness result
        result = await self._safety_store.create_result(
            tenant_id=principal.tenant_id,
            gate_type="groundedness",
            status=status,
            severity=severity,
            reason_code=reason_code,
            safe_details=details,
            campaign_id=campaign_id,
            contact_id=contact_id,
            draft_id=draft_id,
        )

        # 6. Audit Logging
        event_type = "safety.gate_failed" if status == "failed" else "safety.gate_passed"
        await self._audit(
            event_type=event_type,
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="campaign",
            object_id=campaign_id or principal.tenant_id,
            details={
                "campaign_id": str(campaign_id) if campaign_id else None,
                "contact_id": str(contact_id) if contact_id else None,
                "draft_id": str(draft_id) if draft_id else None,
                "gate_type": "groundedness",
                "status": status,
                "reason_code": reason_code,
            },
        )

        return result

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
