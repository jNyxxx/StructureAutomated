"""Tests for Phase 1 Slice P1-04 RAG grounding foundation."""

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
from app.services.rag_grounding import (
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    RAGGroundingService,
    ResearchArtifactRecord,
    chunk_text,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_NOW = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)

_PLAN_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


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


class _FakeKnowledgeStore:
    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, KnowledgeDocumentRecord] = {}
        self.chunks: dict[uuid.UUID, KnowledgeChunkRecord] = {}
        self.artifacts: dict[uuid.UUID, ResearchArtifactRecord] = {}

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


@dataclass
class _FakeContact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str | None = None
    full_name: str | None = None


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


# 1. Migration/offline SQL check
def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


def test_offline_sql_render_includes_knowledge_documents_and_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    assert "CREATE TABLE knowledge_documents" in sql
    assert "CREATE TABLE knowledge_chunks" in sql
    assert "ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE knowledge_documents FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY knowledge_documents_tenant_isolation ON knowledge_documents" in sql
    assert "ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE knowledge_chunks FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY knowledge_chunks_tenant_isolation ON knowledge_chunks" in sql


# 2. Text Chunking Verification
def test_chunk_text_safely() -> None:
    text_content = "This is a document content that is to be split into chunks."
    chunks = chunk_text(text_content, chunk_size=10, overlap=2)
    assert len(chunks) > 0
    # Reassemble check
    assert "".join(chunks[0]) == text_content[:10]


# 3. Document added and chunked tests
@pytest.mark.asyncio
async def test_add_document_success() -> None:
    store = _FakeKnowledgeStore()
    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=_FakeCampaignStore(),
        contact_store=_FakeContactStore(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        audit_record=record_audit,
    )

    doc = await service.add_document(
        principal=_principal(),
        title="CRE Market Report",
        content="Commercial Real Estate values remain stable.",
        source_url="http://cre.report",
        chunk_size=20,
        overlap=5,
        now=_NOW,
    )

    assert doc.title == "CRE Market Report"
    assert doc.status == "active"
    assert len(store.documents) == 1
    assert len(store.chunks) > 1

    # Verify audit events emitted
    assert len(audit_events) == 2
    assert audit_events[0]["event_type"] == "knowledge.document_created"
    assert audit_events[1]["event_type"] == "knowledge.document_chunked"


@pytest.mark.asyncio
async def test_delete_document_success() -> None:
    store = _FakeKnowledgeStore()
    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=_FakeCampaignStore(),
        contact_store=_FakeContactStore(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        audit_record=record_audit,
    )

    doc = await service.add_document(
        principal=_principal(),
        title="Temp doc",
        content="Some temporary details.",
        now=_NOW,
    )

    # Perform soft-delete
    deleted = await service.delete_document(
        principal=_principal(),
        document_id=doc.id,
        now=_NOW,
    )

    assert deleted.status == "deleted"
    # Verify chunks deleted
    assert len(store.chunks) == 0

    assert len(audit_events) == 3
    assert audit_events[2]["event_type"] == "knowledge.document_deleted"


# 4. Retrieval & Grounding tests
@pytest.mark.asyncio
async def test_retrieve_grounding_context_success() -> None:
    store = _FakeKnowledgeStore()
    campaign_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()

    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="contact@cre.com", full_name="John Cre"
    )

    # Setup RAG doc
    doc = await store.create_document(
        tenant_id=_TENANT, title="Guide", content="Use a low leverage strategy for acquisition."
    )
    await store.create_chunks(
        tenant_id=_TENANT,
        document_id=doc.id,
        chunks=["Use a low leverage strategy", "for acquisition."],
    )

    # Setup Research Artifact
    artifact = ResearchArtifactRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        research_run_id=uuid.uuid4(),
        contact_id=_CONTACT,
        findings={"contact_preferences": "prefer phone over email"},
        created_at=_NOW,
    )
    store.artifacts[artifact.id] = artifact

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=campaign_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    # Retrieve grounding context
    res = await service.retrieve_grounding_context(
        principal=_principal(), campaign_id=_CAMPAIGN, contact_id=_CONTACT
    )

    assert len(res.chunks) == 3
    # Artifact chunk included
    assert any(c.source_type == "research_artifact" for c in res.chunks)
    # Document chunks included
    assert any(c.source_type == "knowledge_chunk" for c in res.chunks)


@pytest.mark.asyncio
async def test_retrieve_grounding_context_lexical_match() -> None:
    store = _FakeKnowledgeStore()
    campaign_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()

    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(id=_CONTACT, tenant_id=_TENANT)

    # Setup doc with matching and non-matching chunks
    doc = await store.create_document(
        tenant_id=_TENANT,
        title="CRE Guide",
        content="Relevant term: capitalization rate. Non-matching chunk info.",
    )
    await store.create_chunks(
        tenant_id=_TENANT,
        document_id=doc.id,
        chunks=["capitalization rate analysis", "other random info text"],
    )

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=campaign_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    res = await service.retrieve_grounding_context(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        query="capitalization",
    )

    assert len(res.chunks) == 1
    assert "capitalization rate" in res.chunks[0].content


@pytest.mark.asyncio
async def test_retrieve_grounding_context_inactive_deleted_excluded() -> None:
    store = _FakeKnowledgeStore()
    campaign_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()

    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(id=_CONTACT, tenant_id=_TENANT)

    # Setup deleted doc
    doc1 = await store.create_document(
        tenant_id=_TENANT, title="Deleted Doc", content="Deleted document details."
    )
    await store.create_chunks(tenant_id=_TENANT, document_id=doc1.id, chunks=["deleted info"])
    await store.update_document(
        tenant_id=_TENANT, document_id=doc1.id, status="deleted", deleted_at=_NOW
    )

    # Setup inactive doc
    doc2 = await store.create_document(
        tenant_id=_TENANT, title="Inactive Doc", content="Inactive document details."
    )
    await store.create_chunks(tenant_id=_TENANT, document_id=doc2.id, chunks=["inactive info"])
    await store.update_document(tenant_id=_TENANT, document_id=doc2.id, status="inactive")

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=campaign_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    res = await service.retrieve_grounding_context(
        principal=_principal(), campaign_id=_CAMPAIGN, contact_id=_CONTACT
    )

    # Must be 0 because both docs are excluded (deleted/inactive documents excluded)
    assert len(res.chunks) == 0


@pytest.mark.asyncio
async def test_retrieve_grounding_context_compliance_suppressed_denied() -> None:
    store = _FakeKnowledgeStore()
    campaign_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()

    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="suppressed@cre.com"
    )

    compliance.suppressed_emails.add("suppressed@cre.com")

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=campaign_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        compliance=compliance,
    )

    with pytest.raises(
        AppError, match="Cannot retrieve grounding context for a suppressed contact."
    ):
        await service.retrieve_grounding_context(
            principal=_principal(), campaign_id=_CAMPAIGN, contact_id=_CONTACT
        )


# 5. Security boundaries & denied cases
@pytest.mark.asyncio
async def test_add_document_rbac_denied() -> None:
    store = _FakeKnowledgeStore()
    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=_FakeCampaignStore(),
        contact_store=_FakeContactStore(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    with pytest.raises(AuthorizationError):
        await service.add_document(
            principal=_principal("viewer"), title="CRE", content="Stable", now=_NOW
        )


@pytest.mark.asyncio
async def test_retrieve_grounding_context_cross_tenant_denied() -> None:
    store = _FakeKnowledgeStore()
    campaign_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()

    # Campaign belongs to Tenant 1, Contact belongs to Tenant 2
    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(id=_CONTACT, tenant_id=_OTHER_TENANT)

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=campaign_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
    )

    # Calling under Tenant 1 context -> contact ownership check will raise object auth error
    with pytest.raises(AuthorizationError):
        await service.retrieve_grounding_context(
            principal=_principal(), campaign_id=_CAMPAIGN, contact_id=_CONTACT
        )


@pytest.mark.asyncio
async def test_retrieve_grounding_context_billing_denied() -> None:
    store = _FakeKnowledgeStore()
    campaign_store = _FakeCampaignStore()
    contact_store = _FakeContactStore()

    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    contact_store.contacts[_CONTACT] = _FakeContact(id=_CONTACT, tenant_id=_TENANT)

    service = RAGGroundingService(
        knowledge_store=store,
        campaign_store=campaign_store,
        contact_store=contact_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=False)),
    )

    with pytest.raises(BillingAccessDenied):
        await service.retrieve_grounding_context(
            principal=_principal(), campaign_id=_CAMPAIGN, contact_id=_CONTACT, now=_NOW
        )


@pytest.mark.asyncio
async def test_add_document_rbac_allowed_roles() -> None:
    store = _FakeKnowledgeStore()
    for role in ("owner", "admin", "marketer"):
        service = RAGGroundingService(
            knowledge_store=store,
            campaign_store=_FakeCampaignStore(),
            contact_store=_FakeContactStore(),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
            billing=BillingGateService(_BillingStore(allowed=True)),
        )
        doc = await service.add_document(
            principal=_principal(role),
            title=f"Doc for {role}",
            content="Some content",
            now=_NOW,
        )
        assert doc.title == f"Doc for {role}"


@pytest.mark.asyncio
async def test_add_document_rbac_denied_roles() -> None:
    store = _FakeKnowledgeStore()
    for role in ("reviewer", "viewer", "billing_admin", "support"):
        service = RAGGroundingService(
            knowledge_store=store,
            campaign_store=_FakeCampaignStore(),
            contact_store=_FakeContactStore(),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
            billing=BillingGateService(_BillingStore(allowed=True)),
        )
        with pytest.raises(AuthorizationError):
            await service.add_document(
                principal=_principal(role),
                title=f"Doc for {role}",
                content="Some content",
                now=_NOW,
            )
