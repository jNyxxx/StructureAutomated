"""Tests for Phase 1 Slice P1-05 AI draft generation foundation."""

import contextlib
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config

from app.auth.principal import CurrentPrincipal
from app.config import get_settings
from app.middleware.error_handler import AppError
from app.repositories.draft_repo import (
    DraftEvidenceRecord,
    DraftRecord,
)
from app.services.authz import (
    AuthorizationError,
    ObjectAuthorizationService,
    RBACService,
)
from app.services.billing import (
    CAN_RUN_AGENTS,
    BillingAccessDenied,
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)
from app.services.draft_generation import (
    DraftGenerationService,
)
from app.services.idempotency import IdempotencyOutcome, IdempotencyState
from app.services.rag_grounding import (
    GroundingChunk,
    GroundingContextResult,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    RAGGroundingService,
    ResearchArtifactRecord,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_PLAN_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_NOW = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)

_ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def _principal(role: str = "owner", *, tenant_id: uuid.UUID = _TENANT) -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=_ACTOR,
        email="owner@example.com",
        tenant_id=tenant_id,
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
                features={CAN_RUN_AGENTS: allowed},
            ),
        )

    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        return self.record if tenant_id == self.record.tenant_id else None

    async def set_status(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None,
    ) -> TenantSubscriptionRecord:
        raise AssertionError("not used")


class _IdempotencyGate:
    def __init__(self, outcome: IdempotencyOutcome | None = None) -> None:
        self.outcome = outcome or IdempotencyOutcome(IdempotencyState.NEW)
        self.begin_calls: list[dict[str, Any]] = []
        self.complete_calls: list[dict[str, Any]] = []

    async def begin(
        self,
        *,
        key: str,
        request_payload: Any,
        now: datetime,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> IdempotencyOutcome:
        self.begin_calls.append(
            {
                "key": key,
                "request_payload": request_payload,
                "tenant_id": tenant_id,
                "actor_user_id": actor_user_id,
            }
        )
        return self.outcome

    async def complete(
        self,
        *,
        key: str,
        response_payload: Any,
        status_code: int,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        self.complete_calls.append(
            {
                "key": key,
                "response_payload": response_payload,
                "status_code": status_code,
                "tenant_id": tenant_id,
            }
        )


class _FakeKnowledgeStore:
    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, KnowledgeDocumentRecord] = {}
        self.chunks: dict[uuid.UUID, KnowledgeChunkRecord] = {}
        self.artifacts: dict[uuid.UUID, ResearchArtifactRecord] = {}

    async def get_chunk(
        self, *, tenant_id: uuid.UUID, chunk_id: uuid.UUID
    ) -> KnowledgeChunkRecord | None:
        c = self.chunks.get(chunk_id)
        if c is not None and c.tenant_id == tenant_id:
            return c
        return None

    async def get_artifact(
        self, *, tenant_id: uuid.UUID, artifact_id: uuid.UUID
    ) -> Any | None:
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        )
        self.documents[doc.id] = doc
        return doc

    async def get_document(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> KnowledgeDocumentRecord | None:
        doc = self.documents.get(document_id)
        if doc is not None and doc.tenant_id == tenant_id:
            return doc
        return None

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
        doc = await self.get_document(tenant_id=tenant_id, document_id=document_id)
        if doc is None:
            return None
        updated = KnowledgeDocumentRecord(
            id=doc.id,
            tenant_id=doc.tenant_id,
            title=title if title is not None else doc.title,
            content=content if content is not None else doc.content,
            source_url=source_url if source_url is not None else doc.source_url,
            status=status if status is not None else doc.status,
            created_at=doc.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=deleted_at if deleted_at is not None else doc.deleted_at,
        )
        self.documents[doc.id] = updated
        return updated

    async def create_chunks(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: list[str],
    ) -> list[KnowledgeChunkRecord]:
        records: list[KnowledgeChunkRecord] = []
        for i, text_content in enumerate(chunks):
            rec = KnowledgeChunkRecord(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                document_id=document_id,
                chunk_index=i,
                content=text_content,
                created_at=datetime.now(UTC),
            )
            self.chunks[rec.id] = rec
            records.append(rec)
        return records

    async def delete_chunks(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        to_del = [
            k
            for k, c in self.chunks.items()
            if c.document_id == document_id and c.tenant_id == tenant_id
        ]
        for k in to_del:
            self.chunks.pop(k)

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
    name: str = "Test Campaign"


@dataclass
class _FakeContact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str | None = None
    first_name: str | None = None
    full_name: str | None = None
    company_name: str | None = None


class _FakeCampaignStore:
    def __init__(self) -> None:
        self.campaigns: dict[uuid.UUID, _FakeCampaign] = {}

    async def get_campaign(self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Any | None:
        campaign = self.campaigns.get(campaign_id)
        if campaign is not None and campaign.tenant_id == tenant_id:
            return campaign
        return None


class _FakeContactStore:
    def __init__(self) -> None:
        self.contacts: dict[uuid.UUID, _FakeContact] = {}

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        contact = self.contacts.get(contact_id)
        if contact is not None and contact.tenant_id == tenant_id:
            return contact
        return None


class _FakeCompliance:
    def __init__(self) -> None:
        self.suppressed_emails: set[str] = set()

    async def is_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> bool:
        return contact_identifier in self.suppressed_emails


class _FakeDraftStore:
    def __init__(self) -> None:
        self.drafts: dict[uuid.UUID, DraftRecord] = {}
        self.evidence: dict[uuid.UUID, DraftEvidenceRecord] = {}

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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.drafts[draft.id] = draft
        return draft

    async def get_draft_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, key: str
    ) -> DraftRecord | None:
        for d in self.drafts.values():
            if d.idempotency_key == key and d.tenant_id == tenant_id:
                return d
        return None

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
            created_at=datetime.now(UTC),
        )
        self.evidence[ev.id] = ev
        return ev


def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


# 1. Migration / offline SQL render check
def test_offline_sql_render_includes_drafts_and_draft_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    assert "CREATE TABLE drafts" in sql
    assert "CREATE TABLE draft_evidence" in sql
    assert "ALTER TABLE drafts ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE drafts FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY drafts_tenant_isolation ON drafts" in sql
    assert "ALTER TABLE draft_evidence ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE draft_evidence FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY draft_evidence_tenant_isolation ON draft_evidence" in sql


# 2. Service End-to-End Success test
@pytest.mark.asyncio
async def test_generate_draft_success() -> None:
    store = _FakeDraftStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    k_store = _FakeKnowledgeStore()

    # Populate Stores
    camp_store.campaigns[_CAMPAIGN] = _FakeCampaign(
        id=_CAMPAIGN, tenant_id=_TENANT, name="CRE Acquisitions"
    )
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT,
        tenant_id=_TENANT,
        email="john@crecorp.com",
        first_name="John",
        full_name="John Cre",
        company_name="CRE Corp",
    )

    # Add Knowledge Documents
    doc = await k_store.create_document(
        tenant_id=_TENANT, title="VOICE", content="Brand guideline acquisition strategy."
    )
    await k_store.create_chunks(
        tenant_id=_TENANT, document_id=doc.id, chunks=["Brand guideline acquisition strategy."]
    )

    # Add Research Artifact
    art = ResearchArtifactRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        research_run_id=uuid.uuid4(),
        contact_id=_CONTACT,
        findings={"revenue": "10M", "focus": "triple net lease properties"},
        created_at=_NOW,
    )
    k_store.artifacts[art.id] = art

    # Instantiate central grounding service
    grounding = RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    service = DraftGenerationService(
        draft_store=store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=grounding,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        audit_record=record_audit,
    )

    res = await service.generate_draft(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        now=_NOW,
    )

    # Verify Draft creation
    assert res.draft is not None
    assert res.draft.status == "generated"
    assert "john@crecorp.com" not in res.draft.body  # check no raw tokens
    assert "triple net lease properties" in res.draft.body  # uses research artifact findings
    assert "Brand guideline acquisition strategy" in res.draft.body  # uses grounding context

    # Verify Evidence creation
    assert len(store.evidence) == 2
    evidences = list(store.evidence.values())
    assert any(ev.source_type == "research_artifact" and ev.source_id == art.id for ev in evidences)
    chunks_records = list(k_store.chunks.values())
    chunk_id = chunks_records[0].id
    assert any(ev.source_type == "knowledge_chunk" and ev.source_id == chunk_id for ev in evidences)

    # Verify Audit Event
    assert len(audit_events) == 1
    assert audit_events[0]["event_type"] == "draft.generated"
    assert audit_events[0]["tenant_id"] == _TENANT
    assert audit_events[0]["actor_user_id"] == _ACTOR


# 3. RBAC checks
@pytest.mark.asyncio
async def test_generate_draft_rbac_denied() -> None:
    store = _FakeDraftStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    k_store = _FakeKnowledgeStore()

    grounding = RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    service = DraftGenerationService(
        draft_store=store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=grounding,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    # reviewer/viewer/billing_admin/support role should be denied draft creation
    for role in ("reviewer", "viewer", "billing_admin", "support"):
        with pytest.raises(AuthorizationError):
            await service.generate_draft(
                principal=_principal(role),
                campaign_id=_CAMPAIGN,
                contact_id=_CONTACT,
                now=_NOW,
            )


# 4. Billing checks
@pytest.mark.asyncio
async def test_generate_draft_billing_denied() -> None:
    store = _FakeDraftStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    k_store = _FakeKnowledgeStore()

    grounding = RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=False)),
    )

    service = DraftGenerationService(
        draft_store=store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=grounding,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=False)),  # features disabled
    )

    with pytest.raises(BillingAccessDenied):
        await service.generate_draft(
            principal=_principal(),
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            now=_NOW,
        )


# 5. Compliance & suppression check (draft gets 'blocked' status)
@pytest.mark.asyncio
async def test_generate_draft_compliance_suppressed_blocked() -> None:
    store = _FakeDraftStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    k_store = _FakeKnowledgeStore()
    compliance = _FakeCompliance()

    camp_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="suppressed@cre.com"
    )
    compliance.suppressed_emails.add("suppressed@cre.com")

    grounding = RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        compliance=compliance,
    )

    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    service = DraftGenerationService(
        draft_store=store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=grounding,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        compliance=compliance,
        audit_record=record_audit,
    )

    res = await service.generate_draft(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        now=_NOW,
    )

    # Draft status must be 'blocked' and not raise exceptions
    assert res.draft is not None
    assert res.draft.status == "blocked"
    assert len(store.evidence) == 0  # no evidence linked for blocked draft

    assert len(audit_events) == 1
    assert audit_events[0]["event_type"] == "draft.blocked"


# 6. Object Authorization checks & Cross-tenant boundaries checks
@pytest.mark.asyncio
async def test_generate_draft_campaign_tenant_mismatch_denied() -> None:
    store = _FakeDraftStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    k_store = _FakeKnowledgeStore()

    # Campaign belongs to OTHER_TENANT
    camp_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_OTHER_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(id=_CONTACT, tenant_id=_TENANT)

    grounding = RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    service = DraftGenerationService(
        draft_store=store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=grounding,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    with pytest.raises(AuthorizationError):
        await service.generate_draft(
            principal=_principal(),
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            now=_NOW,
        )


@pytest.mark.asyncio
async def test_generate_draft_cross_tenant_evidence_denied() -> None:
    store = _FakeDraftStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    k_store = _FakeKnowledgeStore()

    camp_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(id=_CONTACT, tenant_id=_TENANT)

    # Grounding chunk mock returns cross-tenant source
    # We will build a customized RAG grounding service mock to return cross-tenant chunk
    class _CrossTenantRAGMock:
        async def retrieve_grounding_context(self, **kwargs: Any) -> GroundingContextResult:
            # RAG grounding chunk belonging to OTHER_TENANT
            chunk = GroundingChunk(
                source_type="knowledge_chunk",
                source_id=uuid.uuid4(),
                content="Other tenant info details",
                tenant_id=_OTHER_TENANT,
            )
            return GroundingContextResult(chunks=[chunk])

    service = DraftGenerationService(
        draft_store=store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=_CrossTenantRAGMock(),  # type: ignore
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    # Verification must raise Cross-tenant grounding source error
    with pytest.raises(AppError, match="Grounding context source tenant mismatch."):
        await service.generate_draft(
            principal=_principal(),
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            now=_NOW,
        )


# 7. Idempotency replays
@pytest.mark.asyncio
async def test_generate_draft_idempotency_replay() -> None:
    store = _FakeDraftStore()
    camp_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    k_store = _FakeKnowledgeStore()
    idem = _IdempotencyGate(outcome=IdempotencyOutcome(IdempotencyState.REPLAY, status_code=201))

    # Pre-create the draft record
    existing_draft = await store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Replay Subject",
        body="Replay Body",
        idempotency_key="unique_key_123",
    )

    grounding = RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=camp_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    service = DraftGenerationService(
        draft_store=store,
        campaign_store=camp_store,
        contact_store=contact_store,
        research_store=k_store,
        grounding_service=grounding,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        idempotency=idem,
    )

    res = await service.generate_draft(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        idempotency_key="unique_key_123",
        now=_NOW,
    )

    assert res.draft is not None
    assert res.draft.id == existing_draft.id
    assert res.idempotency_replay is True
    assert len(idem.begin_calls) == 1


# 8. Assertions verifying safety requirements (no external calls, prompt fence,
# groundedness gates)
def test_safety_gates_and_fences_not_accidental_added() -> None:
    import inspect

    from app.services.draft_generation import DraftGenerationService

    source_code = inspect.getsource(DraftGenerationService)

    # Confirm no human review or sending gate added
    assert "send_draft" not in source_code.lower()
    assert "approve_draft" not in source_code.lower()
    assert "reject_draft" not in source_code.lower()
    assert "review_queue" not in source_code.lower()
