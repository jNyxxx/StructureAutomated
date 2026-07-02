"""P4-LocalDockerE2E-Fix-4: chained grounded happy path, service-level.

Exercises seed -> draft generation -> human approval -> send-gate dry run ->
mock send intent -> outbound/audit, using the same fully-wired service
composition as backend/app/routers/drafts.py, review.py, and sending.py. Also
pins the fail-closed regression this seed fixes: no grounding data still
produces ``needs_regeneration`` and never reaches the review queue.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from app.auth.principal import CurrentPrincipal
from app.repositories.draft_repo import DraftEvidenceRecord, DraftRecord
from app.repositories.review_repo import ReviewRecord
from app.repositories.sending_repo import OutboundMessageRecord, SendGateResultRecord
from app.scripts.seed_local_grounding import (
    SEED_DOC_TITLE,
    build_seed_principal,
    seed_grounding_document,
)
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import (
    CAN_RUN_AGENTS,
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)
from app.services.draft_generation import DraftGenerationService
from app.services.groundedness import GroundednessService
from app.services.mock_sender import MockSenderService
from app.services.rag_grounding import (
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    RAGGroundingService,
    ResearchArtifactRecord,
)
from app.services.review import ReviewService
from app.services.safety import SafetyGateResultRecord, SafetyService
from app.services.send_gate import SendGateService

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_PLAN_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)


def _principal(role: str = "owner") -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=_ACTOR,
        email="owner@example.com",
        tenant_id=_TENANT,
        role=role,
        membership_version=1,
        mfa_verified=True,
    )


class _BillingStore:
    def __init__(self, *, allowed: bool = True) -> None:
        self.record = TenantSubscriptionRecord(
            tenant_id=_TENANT,
            tenant_status="active",
            plan=BillingPlan(
                id=_PLAN_ID,
                key="mvp_mock",
                name="MVP Mock Plan",
                features={CAN_RUN_AGENTS: allowed, "can_send": allowed},
            ),
        )

    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        return self.record if tenant_id == self.record.tenant_id else None

    async def set_status(
        self, *, tenant_id: uuid.UUID, tenant_status: str, grace_until: datetime | None
    ) -> TenantSubscriptionRecord:
        raise AssertionError("not used")


class _FakeKnowledgeStore:
    """In-memory double for KnowledgeRepository, mirroring test_draft_generation.py."""

    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, KnowledgeDocumentRecord] = {}
        self.chunks: dict[uuid.UUID, KnowledgeChunkRecord] = {}
        self.artifacts: dict[uuid.UUID, ResearchArtifactRecord] = {}

    async def get_chunk(
        self, *, tenant_id: uuid.UUID, chunk_id: uuid.UUID
    ) -> KnowledgeChunkRecord | None:
        c = self.chunks.get(chunk_id)
        return c if c is not None and c.tenant_id == tenant_id else None

    async def get_artifact(self, *, tenant_id: uuid.UUID, artifact_id: uuid.UUID) -> Any | None:
        return None

    async def create_document(
        self,
        *,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        source_url: str | None = None,
        status: str = "active",
    ) -> KnowledgeDocumentRecord:
        doc = KnowledgeDocumentRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title=title,
            content=content,
            source_url=source_url,
            status=status,
            created_at=_NOW,
            updated_at=_NOW,
            deleted_at=None,
        )
        self.documents[doc.id] = doc
        return doc

    async def get_document(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> KnowledgeDocumentRecord | None:
        doc = self.documents.get(document_id)
        return doc if doc is not None and doc.tenant_id == tenant_id else None

    async def get_document_by_title(
        self, *, tenant_id: uuid.UUID, title: str
    ) -> KnowledgeDocumentRecord | None:
        for doc in self.documents.values():
            if (
                doc.tenant_id == tenant_id
                and doc.title == title
                and doc.status == "active"
                and doc.deleted_at is None
            ):
                return doc
        return None

    async def create_chunks(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID, chunks: list[str]
    ) -> list[KnowledgeChunkRecord]:
        records: list[KnowledgeChunkRecord] = []
        for i, text_content in enumerate(chunks):
            rec = KnowledgeChunkRecord(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                document_id=document_id,
                chunk_index=i,
                content=text_content,
                created_at=_NOW,
            )
            self.chunks[rec.id] = rec
            records.append(rec)
        return records

    async def list_chunks_for_grounding(
        self, *, tenant_id: uuid.UUID
    ) -> list[KnowledgeChunkRecord]:
        recs: list[KnowledgeChunkRecord] = []
        for c in self.chunks.values():
            doc = self.documents.get(c.document_id)
            if (
                c.tenant_id == tenant_id
                and doc is not None
                and doc.status == "active"
                and doc.deleted_at is None
            ):
                recs.append(c)
        return recs

    async def get_research_artifact_for_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ResearchArtifactRecord | None:
        for a in self.artifacts.values():
            if a.contact_id == contact_id and a.tenant_id == tenant_id:
                return a
        return None


@dataclass
class _FakeCampaign:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str = "E2E Fix-4 Grounded Happy Path"


@dataclass
class _FakeContact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str | None = "john@crecorp.example"
    full_name: str | None = "John Cre"
    company_name: str | None = "CRE Corp"


class _FakeCampaignStore:
    def __init__(self) -> None:
        self.campaigns: dict[uuid.UUID, _FakeCampaign] = {
            _CAMPAIGN: _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
        }

    async def get_campaign(self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Any | None:
        c = self.campaigns.get(campaign_id)
        return c if c is not None and c.tenant_id == tenant_id else None


class _FakeContactStore:
    def __init__(self) -> None:
        self.contacts: dict[uuid.UUID, _FakeContact] = {
            _CONTACT: _FakeContact(id=_CONTACT, tenant_id=_TENANT)
        }

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        c = self.contacts.get(contact_id)
        return c if c is not None and c.tenant_id == tenant_id else None


class _FakeCompliance:
    def __init__(self) -> None:
        self.suppressed_emails: set[str] = set()

    async def is_suppressed(
        self, *, tenant_id: uuid.UUID, channel: str, contact_identifier: str
    ) -> bool:
        return contact_identifier in self.suppressed_emails


class _FakeDraftStore:
    def __init__(self) -> None:
        self.drafts: dict[uuid.UUID, DraftRecord] = {}
        self.evidence: list[DraftEvidenceRecord] = []

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
        draft = DraftRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=status,
            subject=subject,
            body=body,
            idempotency_key=idempotency_key,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.drafts[draft.id] = draft
        return draft

    async def get_draft_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, key: str
    ) -> DraftRecord | None:
        for d in self.drafts.values():
            if d.tenant_id == tenant_id and d.idempotency_key == key:
                return d
        return None

    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> DraftRecord | None:
        d = self.drafts.get(draft_id)
        return d if d is not None and d.tenant_id == tenant_id else None

    async def update_draft_status(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID, status: str
    ) -> DraftRecord | None:
        draft = self.drafts.get(draft_id)
        if draft is None or draft.tenant_id != tenant_id:
            return None
        updated = DraftRecord(
            id=draft.id,
            tenant_id=draft.tenant_id,
            campaign_id=draft.campaign_id,
            contact_id=draft.contact_id,
            status=status,
            subject=draft.subject,
            body=draft.body,
            idempotency_key=draft.idempotency_key,
            created_at=draft.created_at,
            updated_at=_NOW,
        )
        self.drafts[draft.id] = updated
        return updated

    async def create_evidence(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        content_snippet: str,
    ) -> DraftEvidenceRecord:
        ev = DraftEvidenceRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            draft_id=draft_id,
            source_type=source_type,
            source_id=source_id,
            content_snippet=content_snippet,
            created_at=_NOW,
        )
        self.evidence.append(ev)
        return ev


class _FakeSafetyStore:
    def __init__(self) -> None:
        self.results: dict[uuid.UUID, SafetyGateResultRecord] = {}

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
        rec = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            draft_id=draft_id,
            gate_type=gate_type,
            status=status,
            severity=severity,
            reason_code=reason_code,
            safe_details=safe_details,
            created_at=_NOW,
        )
        self.results[rec.id] = rec
        return rec

    async def update_result_draft_id(
        self, *, tenant_id: uuid.UUID, result_id: uuid.UUID, draft_id: uuid.UUID
    ) -> SafetyGateResultRecord | None:
        rec = self.results.get(result_id)
        if rec is None or rec.tenant_id != tenant_id:
            return None
        updated = SafetyGateResultRecord(
            id=rec.id,
            tenant_id=rec.tenant_id,
            campaign_id=rec.campaign_id,
            contact_id=rec.contact_id,
            draft_id=draft_id,
            gate_type=rec.gate_type,
            status=rec.status,
            severity=rec.severity,
            reason_code=rec.reason_code,
            safe_details=rec.safe_details,
            created_at=rec.created_at,
        )
        self.results[rec.id] = updated
        return updated

    async def list_results_for_context(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> list[SafetyGateResultRecord]:
        results = []
        for r in self.results.values():
            if r.tenant_id != tenant_id:
                continue
            if draft_id is not None and r.draft_id != draft_id:
                continue
            results.append(r)
        return results


class _FakeReviewStore:
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ReviewRecord] = {}

    async def create_review_item(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str = "pending_review",
    ) -> ReviewRecord:
        item = ReviewRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            draft_id=draft_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=status,
            reviewer_user_id=None,
            action_reason=None,
            reviewed_at=None,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.items[item.id] = item
        return item

    async def get_review_item(
        self, *, tenant_id: uuid.UUID, review_id: uuid.UUID
    ) -> ReviewRecord | None:
        item = self.items.get(review_id)
        return item if item is not None and item.tenant_id == tenant_id else None

    async def get_review_item_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> ReviewRecord | None:
        for item in self.items.values():
            if item.draft_id == draft_id and item.tenant_id == tenant_id:
                return item
        return None

    async def update_review_status(
        self,
        *,
        tenant_id: uuid.UUID,
        review_id: uuid.UUID,
        status: str,
        reviewer_user_id: uuid.UUID | None = None,
        action_reason: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> ReviewRecord | None:
        item = self.items.get(review_id)
        if item is None or item.tenant_id != tenant_id:
            return None
        updated = ReviewRecord(
            id=item.id,
            tenant_id=item.tenant_id,
            draft_id=item.draft_id,
            campaign_id=item.campaign_id,
            contact_id=item.contact_id,
            status=status,
            reviewer_user_id=reviewer_user_id,
            action_reason=action_reason,
            reviewed_at=reviewed_at,
            created_at=item.created_at,
            updated_at=_NOW,
        )
        self.items[item.id] = updated
        return updated

    async def list_review_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[ReviewRecord]:
        results = []
        for item in self.items.values():
            if item.tenant_id != tenant_id:
                continue
            if campaign_id is not None and item.campaign_id != campaign_id:
                continue
            if status is not None and item.status != status:
                continue
            results.append(item)
        return results


class _FakeSendingStore:
    def __init__(self) -> None:
        self.gate_results: dict[uuid.UUID, SendGateResultRecord] = {}
        self.outbound_messages: dict[uuid.UUID, OutboundMessageRecord] = {}

    async def create_gate_result(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        deny_reason_code: str | None = None,
    ) -> SendGateResultRecord:
        res = SendGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            draft_id=draft_id,
            status=status,
            deny_reason_code=deny_reason_code,
            created_at=_NOW,
        )
        self.gate_results[res.id] = res
        return res

    async def get_outbound_message_by_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> OutboundMessageRecord | None:
        for m in self.outbound_messages.values():
            if m.tenant_id == tenant_id and m.draft_id == draft_id:
                return m
        return None

    async def create_outbound_message(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        sent_at: datetime | None = None,
    ) -> OutboundMessageRecord:
        msg = OutboundMessageRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            draft_id=draft_id,
            status=status,
            sent_at=sent_at,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.outbound_messages[msg.id] = msg
        return msg


def _build_services(
    *,
    k_store: _FakeKnowledgeStore,
    camp_store: _FakeCampaignStore,
    contact_store: _FakeContactStore,
    draft_store: _FakeDraftStore,
    safety_store: _FakeSafetyStore,
    review_store: _FakeReviewStore,
    sending_store: _FakeSendingStore,
    compliance: _FakeCompliance,
    audit_events: list[dict[str, Any]],
) -> tuple[
    DraftGenerationService, ReviewService, SendGateService, MockSenderService, RAGGroundingService
]:
    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    billing = BillingGateService(_BillingStore(allowed=True))
    rbac = RBACService()
    object_authz = ObjectAuthorizationService()

    grounding = RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        rbac=rbac,
        object_authz=object_authz,
        billing=billing,
        compliance=compliance,
        audit_record=record_audit,
    )
    safety = SafetyService(
        safety_store=safety_store, knowledge_store=k_store, audit_record=record_audit
    )
    groundedness = GroundednessService(
        safety_store=safety_store,
        knowledge_store=k_store,
        research_store=k_store,
        audit_record=record_audit,
    )

    draft_service = DraftGenerationService(
        draft_store=draft_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=grounding,
        rbac=rbac,
        object_authz=object_authz,
        billing=billing,
        safety_service=safety,
        groundedness_service=groundedness,
        compliance=compliance,
        review_store=review_store,
        audit_record=record_audit,
    )
    review_service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=rbac,
        compliance=compliance,
        audit_record=record_audit,
    )
    send_gate = SendGateService(
        sending_store=sending_store,
        draft_store=draft_store,
        review_store=review_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=rbac,
        object_authz=object_authz,
        compliance=compliance,
        audit_record=record_audit,
    )
    sender = MockSenderService(
        sending_store=sending_store, send_gate=send_gate, audit_record=record_audit
    )

    return draft_service, review_service, send_gate, sender, grounding


@pytest.mark.asyncio
async def test_seeded_grounding_produces_generated_draft_through_mock_send() -> None:
    k_store = _FakeKnowledgeStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    review_store = _FakeReviewStore()
    sending_store = _FakeSendingStore()
    compliance = _FakeCompliance()
    audit_events: list[dict[str, Any]] = []

    draft_service, review_service, send_gate, sender, grounding = _build_services(
        k_store=k_store,
        camp_store=camp_store,
        contact_store=contact_store,
        draft_store=draft_store,
        safety_store=safety_store,
        review_store=review_store,
        sending_store=sending_store,
        compliance=compliance,
        audit_events=audit_events,
    )

    # 1. Seed deterministic local grounding data through the gated add_document path.
    seed_principal = build_seed_principal(_TENANT)
    seed_result = await seed_grounding_document(
        knowledge_repo=k_store,
        grounding_service=grounding,
        principal=seed_principal,
        now=_NOW,
    )
    assert seed_result.created is True
    assert seed_result.chunk_count >= 1

    # Seeding twice is a no-op (idempotent).
    replay = await seed_grounding_document(
        knowledge_repo=k_store, grounding_service=grounding, principal=seed_principal, now=_NOW
    )
    assert replay.created is False
    assert replay.skipped_reason == "already_seeded"
    assert sum(1 for d in k_store.documents.values() if d.title == SEED_DOC_TITLE) == 1

    # 2. Draft generation now finds grounding evidence and produces a generated draft.
    res = await draft_service.generate_draft(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        idempotency_key="e2e-happy-path-draft",
        now=_NOW,
    )
    assert res.draft is not None
    assert res.draft.status == "generated"

    evidence = [e for e in draft_store.evidence if e.draft_id == res.draft.id]
    assert any(e.source_type == "knowledge_chunk" for e in evidence)

    gate_results = await safety_store.list_results_for_context(
        tenant_id=_TENANT, draft_id=res.draft.id
    )
    gate_types = {r.gate_type: r.status for r in gate_results}
    assert gate_types == {
        "prompt_injection": "passed",
        "source_trust": "passed",
        "groundedness": "passed",
    }

    pending = await review_store.list_review_queue(tenant_id=_TENANT, status="pending_review")
    assert len(pending) == 1
    review_item = pending[0]
    assert review_item.draft_id == res.draft.id

    # 3. Human approval.
    approved = await review_service.approve_draft(
        _principal("owner"), review_id=review_item.id, now=_NOW
    )
    assert approved.status == "approved"

    # 4. Send-gate dry run (no outbound message yet).
    dry_run_result = await send_gate.evaluate_gate(
        principal=_principal("owner"), draft_id=res.draft.id, now=_NOW
    )
    assert dry_run_result.status == "passed"
    assert len(sending_store.outbound_messages) == 0

    # 5. Mock send intent.
    send_result = await sender.send_approved_draft(
        _principal("owner"), draft_id=res.draft.id, now=_NOW
    )
    assert send_result.status == "mock_sent"

    # 6. Outbound read.
    outbound = await sending_store.get_outbound_message_by_draft(
        tenant_id=_TENANT, draft_id=res.draft.id
    )
    assert outbound is not None
    assert outbound.status == "mock_sent"

    # 7. Audit trail covers the whole chain; no gate-failure events anywhere.
    event_types = {a["event_type"] for a in audit_events}
    assert {
        "knowledge.document_created",
        "knowledge.document_chunked",
        "draft.generated",
        "draft.approved",
        "send_gate.passed",
        "outbound_message.sent",
    }.issubset(event_types)
    assert "safety.gate_failed" not in event_types
    assert "send_gate.failed" not in event_types
    assert "draft.needs_regeneration" not in event_types


@pytest.mark.asyncio
async def test_generate_draft_with_no_grounding_data_needs_regeneration() -> None:
    """Regression proof: without seeded grounding data, generation stays fail-closed."""
    k_store = _FakeKnowledgeStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    review_store = _FakeReviewStore()
    sending_store = _FakeSendingStore()
    compliance = _FakeCompliance()
    audit_events: list[dict[str, Any]] = []

    draft_service, _review_service, _send_gate, _sender, _grounding = _build_services(
        k_store=k_store,
        camp_store=camp_store,
        contact_store=contact_store,
        draft_store=draft_store,
        safety_store=safety_store,
        review_store=review_store,
        sending_store=sending_store,
        compliance=compliance,
        audit_events=audit_events,
    )

    res = await draft_service.generate_draft(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        now=_NOW,
    )

    assert res.draft is not None
    assert res.draft.status == "needs_regeneration"

    groundedness_results = [
        r
        for r in safety_store.results.values()
        if r.gate_type == "groundedness" and r.draft_id == res.draft.id
    ]
    assert len(groundedness_results) == 1
    assert groundedness_results[0].status == "failed"
    assert groundedness_results[0].reason_code == "no_evidence_provided"

    queue = await review_store.list_review_queue(tenant_id=_TENANT)
    assert queue == []
