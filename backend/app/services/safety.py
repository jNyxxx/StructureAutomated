"""Safety gate evaluation service for Phase 1 Slice P1-06."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.rag_grounding import GroundingChunk, KnowledgeStore


@dataclass(frozen=True)
class SafetyGateResultRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    draft_id: uuid.UUID | None
    gate_type: str
    status: str
    severity: str
    reason_code: str
    safe_details: dict[str, Any]
    created_at: datetime


class SafetyStore(Protocol):
    async def create_result(
        self,
        *,
        tenant_id: uuid.UUID,
        gate_type: str,
        status: str,
        severity: str,
        reason_code: str,
        safe_details: dict[str, Any],
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> SafetyGateResultRecord:
        """Persist safety evaluation result."""

    async def update_result_draft_id(
        self, *, tenant_id: uuid.UUID, result_id: uuid.UUID, draft_id: uuid.UUID
    ) -> SafetyGateResultRecord | None:
        """Link a safety result to a draft."""


AuditRecorder = Any


class SafetyService:
    """Safety gate checks for prompt injection and source trust."""

    def __init__(
        self,
        *,
        safety_store: SafetyStore,
        knowledge_store: KnowledgeStore,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._safety_store = safety_store
        self._knowledge_store = knowledge_store
        self._audit_record = audit_record

    async def evaluate_grounding_safety(
        self,
        *,
        principal: CurrentPrincipal,
        chunks: list[GroundingChunk],
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> list[SafetyGateResultRecord]:
        """Evaluate prompt injection and source trust for grounding chunks."""
        # 1. Tenant boundary check
        for chunk in chunks:
            if chunk.tenant_id != principal.tenant_id:
                raise AppError(
                    "CROSS_TENANT_GROUNDING_SOURCE",
                    "Grounding context source tenant mismatch.",
                    status_code=403,
                )

        results: list[SafetyGateResultRecord] = []

        # 2. Prompt Injection Evaluation
        injection_found = False
        failed_chunk_ids: list[str] = []
        patterns = ("ignore previous instructions", "system prompt", "jailbreak")

        for chunk in chunks:
            content_lower = chunk.content.lower()
            if any(pat in content_lower for pat in patterns):
                injection_found = True
                failed_chunk_ids.append(str(chunk.source_id))

        if injection_found:
            pi_status = "failed"
            pi_severity = "critical"
            pi_reason = "prompt_injection_detected"
            pi_details = {"failed_chunk_ids": failed_chunk_ids}
        else:
            pi_status = "passed"
            pi_severity = "info"
            pi_reason = "passed"
            pi_details = {}

        pi_record = await self._safety_store.create_result(
            tenant_id=principal.tenant_id,
            gate_type="prompt_injection",
            status=pi_status,
            severity=pi_severity,
            reason_code=pi_reason,
            safe_details=pi_details,
            campaign_id=campaign_id,
            contact_id=contact_id,
            draft_id=draft_id,
        )
        results.append(pi_record)

        # 3. Source Trust Evaluation
        source_failed_urls: list[str] = []
        source_warning_urls: list[str] = []

        for chunk in chunks:
            if chunk.source_type == "knowledge_chunk":
                chunk_rec = await self._knowledge_store.get_chunk(
                    tenant_id=principal.tenant_id, chunk_id=chunk.source_id
                )
                if chunk_rec is not None:
                    doc = await self._knowledge_store.get_document(
                        tenant_id=principal.tenant_id, document_id=chunk_rec.document_id
                    )
                    if doc is not None and doc.source_url:
                        url = doc.source_url.lower()
                        if "untrusted.org" in url or "malicious-site.com" in url:
                            source_failed_urls.append(doc.source_url)
                        elif "reddit.com" in url or "wikipedia.org" in url:
                            source_warning_urls.append(doc.source_url)

        if source_failed_urls:
            st_status = "failed"
            st_severity = "high"
            st_reason = "untrusted_sources_detected"
            st_details = {"failed_urls": source_failed_urls}
        elif source_warning_urls:
            st_status = "warning"
            st_severity = "medium"
            st_reason = "warning_sources_detected"
            st_details = {"warning_urls": source_warning_urls}
        else:
            st_status = "passed"
            st_severity = "info"
            st_reason = "passed"
            st_details = {}

        st_record = await self._safety_store.create_result(
            tenant_id=principal.tenant_id,
            gate_type="source_trust",
            status=st_status,
            severity=st_severity,
            reason_code=st_reason,
            safe_details=st_details,
            campaign_id=campaign_id,
            contact_id=contact_id,
            draft_id=draft_id,
        )
        results.append(st_record)

        # 4. Audit Logging
        overall_failed = pi_status == "failed" or st_status == "failed"
        event_type = "safety.gate_failed" if overall_failed else "safety.gate_passed"

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
                "prompt_injection_status": pi_status,
                "source_trust_status": st_status,
            },
        )

        return results

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
