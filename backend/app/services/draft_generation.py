"""AI draft generation service for Phase 1 Slice P1-05."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.draft_repo import (
    DraftEvidenceRecord,
    DraftRecord,
)
from app.services.authz import (
    CAN_CREATE_DRAFT,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)
from app.services.billing import CAN_RUN_AGENTS as BILLING_CAN_RUN_AGENTS
from app.services.billing import BillingGateService
from app.services.idempotency import IdempotencyOutcome, IdempotencyState
from app.services.rag_grounding import RAGGroundingService
from app.services.safety import SafetyService


@dataclass(frozen=True)
class DraftCreateResult:
    """Result of draft creation."""

    draft: DraftRecord | None
    idempotency_replay: bool = False


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


class ResearchStore(Protocol):
    async def get_research_artifact_for_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Any | None:
        """Get latest research artifact findings."""


class IdempotencyGate(Protocol):
    async def begin(
        self,
        *,
        key: str,
        request_payload: Any,
        now: datetime,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> IdempotencyOutcome:
        """Begin idempotent operation."""

    async def complete(
        self,
        *,
        key: str,
        response_payload: Any,
        status_code: int,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        """Complete idempotent operation."""


class DraftStore(Protocol):
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
        """Create a draft record."""

    async def get_draft_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, key: str
    ) -> DraftRecord | None:
        """Retrieve existing draft by idempotency key."""

    async def create_evidence(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        content_snippet: str,
    ) -> DraftEvidenceRecord:
        """Link evidence to a draft."""


AuditRecorder = Any


def _obj(record: Any | None) -> TenantOwnedObject | None:
    if record is None:
        return None
    return TenantOwnedObject(id=record.id, tenant_id=record.tenant_id)


class DraftGenerationService:
    """Mock AI draft generation service with structured records and grounding evidence."""

    def __init__(
        self,
        *,
        draft_store: DraftStore,
        campaign_store: GroundingCampaignStore,
        contact_store: GroundingContactStore,
        research_store: ResearchStore,
        grounding_service: RAGGroundingService,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
        billing: BillingGateService,
        safety_service: SafetyService | None = None,
        compliance: ComplianceGate | None = None,
        idempotency: IdempotencyGate | None = None,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._draft_store = draft_store
        self._campaign_store = campaign_store
        self._contact_store = contact_store
        self._research_store = research_store
        self._grounding_service = grounding_service
        self._rbac = rbac
        self._object_authz = object_authz
        self._billing = billing
        self._safety_service = safety_service
        self._compliance = compliance
        self._idempotency = idempotency
        self._audit_record = audit_record

    async def generate_draft(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        idempotency_key: str | None = None,
        now: datetime,
    ) -> DraftCreateResult:
        # 1. RBAC Check
        self._rbac.require(principal, CAN_CREATE_DRAFT)

        # 2. Billing Check
        await self._billing.require_feature(principal.tenant_id, BILLING_CAN_RUN_AGENTS, now=now)

        # 3. Idempotency Check
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
        }
        if self._idempotency is not None and idempotency_key is not None:
            outcome = await self._idempotency.begin(
                key=idempotency_key,
                request_payload=request_payload,
                now=now,
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
            if outcome.is_replay:
                existing = await self._draft_store.get_draft_by_idempotency_key(
                    tenant_id=principal.tenant_id, key=idempotency_key
                )
                return DraftCreateResult(draft=existing, idempotency_replay=True)
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "DRAFT_CREATE_IN_PROGRESS",
                    "Draft generation is already in progress.",
                    status_code=409,
                )

        # 4. Fetch Campaign and Contact & enforce Object Authorization
        campaign = await self._campaign_store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(campaign))
        if campaign is None:
            raise AppError("CAMPAIGN_NOT_FOUND", "Campaign not found.", status_code=404)

        contact = await self._contact_store.get_contact(
            tenant_id=principal.tenant_id, contact_id=contact_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(contact))
        if contact is None:
            raise AppError("CONTACT_NOT_FOUND", "Contact not found.", status_code=404)

        # 5. Compliance check (suppression gate)
        is_suppressed = False
        if self._compliance is not None and contact.email:
            is_suppressed = await self._compliance.is_suppressed(
                tenant_id=principal.tenant_id, channel="email", contact_identifier=contact.email
            )

        if is_suppressed:
            # Create a blocked draft record and return immediately
            draft = await self._draft_store.create_draft(
                tenant_id=principal.tenant_id,
                campaign_id=campaign_id,
                contact_id=contact_id,
                status="blocked",
                subject=f"Blocked Draft - {campaign.name}",
                body="Draft generation blocked due to contact email suppression.",
                idempotency_key=idempotency_key,
            )

            # Audit blocked event
            await self._audit(
                event_type="draft.blocked",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft.id,
                details={"campaign_id": str(campaign_id), "contact_id": str(contact_id)},
            )

            if self._idempotency is not None and idempotency_key is not None:
                await self._idempotency.complete(
                    key=idempotency_key,
                    response_payload={"draft_id": str(draft.id)},
                    status_code=201,
                    tenant_id=principal.tenant_id,
                )

            return DraftCreateResult(draft=draft)

        # 6. Retrieve grounding context (which also does a secondary billing/object check)
        context_res = await self._grounding_service.retrieve_grounding_context(
            principal=principal,
            campaign_id=campaign_id,
            contact_id=contact_id,
            now=now,
        )

        # 7. Same-tenant boundary checking
        # Verify that all returned grounding chunk source records are owned by
        # the principal's tenant
        for chunk in context_res.chunks:
            # RAGGroundingService retrieve_grounding_context internally isolates,
            # but we explicitly assert cross-tenant safety here
            if hasattr(chunk, "tenant_id") and chunk.tenant_id != principal.tenant_id:
                raise AppError(
                    "CROSS_TENANT_GROUNDING_SOURCE",
                    "Grounding context source tenant mismatch.",
                    status_code=403,
                )

        # 7.5 Run safety evaluation if safety service is configured
        safety_results = []
        if self._safety_service is not None:
            safety_results = await self._safety_service.evaluate_grounding_safety(
                principal=principal,
                chunks=context_res.chunks,
                campaign_id=campaign_id,
                contact_id=contact_id,
            )
            any_failed = any(res.status == "failed" for res in safety_results)
            if any_failed:
                # Create a blocked draft record and return immediately
                draft = await self._draft_store.create_draft(
                    tenant_id=principal.tenant_id,
                    campaign_id=campaign_id,
                    contact_id=contact_id,
                    status="blocked",
                    subject=f"Blocked Draft - {campaign.name}",
                    body="Draft generation blocked due to safety gate failure.",
                    idempotency_key=idempotency_key,
                )

                # Link evidence to retrieved grounding chunks
                for chunk in context_res.chunks:
                    await self._draft_store.create_evidence(
                        tenant_id=principal.tenant_id,
                        draft_id=draft.id,
                        source_type=chunk.source_type,
                        source_id=chunk.source_id,
                        content_snippet=chunk.content[:500],
                    )

                # Link safety results to the draft ID
                for res in safety_results:
                    await self._safety_service._safety_store.update_result_draft_id(
                        tenant_id=principal.tenant_id,
                        result_id=res.id,
                        draft_id=draft.id,
                    )

                # Audit blocked event
                await self._audit(
                    event_type="draft.blocked",
                    tenant_id=principal.tenant_id,
                    actor_user_id=principal.user_id,
                    object_type="draft",
                    object_id=draft.id,
                    details={
                        "campaign_id": str(campaign_id),
                        "contact_id": str(contact_id),
                        "reason": "safety_gate_failure",
                    },
                )

                if self._idempotency is not None and idempotency_key is not None:
                    await self._idempotency.complete(
                        key=idempotency_key,
                        response_payload={"draft_id": str(draft.id)},
                        status_code=201,
                        tenant_id=principal.tenant_id,
                    )

                return DraftCreateResult(draft=draft)

        # 8. Deterministic mock draft generation
        findings_snippets = []
        document_snippets = []
        for chunk in context_res.chunks:
            if chunk.source_type == "research_artifact":
                findings_snippets.append(chunk.content)
            elif chunk.source_type == "knowledge_chunk":
                document_snippets.append(chunk.content)

        findings_str = findings_snippets[0] if findings_snippets else "standard business research"
        doc_str = document_snippets[0] if document_snippets else "general brand voice parameters"

        subject = (
            f"Intro: Proposed CRE acquisition structure for {contact.company_name or 'your firm'}"
        )
        body = (
            f"Dear {contact.full_name or 'prospect'},\n\n"
            f"I hope this finds you well. Based on our research findings: {findings_str}.\n"
            f"We would like to introduce the following structure "
            f"based on our guidelines: {doc_str}.\n\n"
            f"Let us know if you'd be interested in discussing.\n"
            f"Best regards,\nCRE Automated Acquisition Team"
        )

        # 9. Create draft record in store
        draft = await self._draft_store.create_draft(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status="generated",
            subject=subject,
            body=body,
            idempotency_key=idempotency_key,
        )

        # Link safety results to the draft ID (if safety check was run)
        if self._safety_service is not None:
            for res in safety_results:
                await self._safety_service._safety_store.update_result_draft_id(
                    tenant_id=principal.tenant_id,
                    result_id=res.id,
                    draft_id=draft.id,
                )

        # 10. Link evidence to retrieved grounding chunks
        for chunk in context_res.chunks:
            await self._draft_store.create_evidence(
                tenant_id=principal.tenant_id,
                draft_id=draft.id,
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                content_snippet=chunk.content[:500],
            )

        # 11. Audit draft generated event
        await self._audit(
            event_type="draft.generated",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="draft",
            object_id=draft.id,
            details={"campaign_id": str(campaign_id), "contact_id": str(contact_id)},
        )

        # 12. Idempotency Complete
        if self._idempotency is not None and idempotency_key is not None:
            await self._idempotency.complete(
                key=idempotency_key,
                response_payload={"draft_id": str(draft.id)},
                status_code=201,
                tenant_id=principal.tenant_id,
            )

        return DraftCreateResult(draft=draft)

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
