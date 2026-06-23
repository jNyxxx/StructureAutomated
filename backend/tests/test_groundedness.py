"""Tests for Phase 1 Slice P1-07 groundedness validation gate."""

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
from app.services.groundedness import GroundednessService
from app.services.rag_grounding import (
    GroundingChunk,
    GroundingContextResult,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    ResearchArtifactRecord,
)
from app.services.safety import (
    SafetyGateResultRecord,
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
        record = SafetyGateResultRecord(
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
            created_at=datetime.now(UTC),
        )
        self.results[record.id] = record
        return record

    async def update_result_draft_id(
        self, *, tenant_id: uuid.UUID, result_id: uuid.UUID, draft_id: uuid.UUID
    ) -> SafetyGateResultRecord | None:
        if result_id in self.results:
            r = self.results[result_id]
            if r.tenant_id != tenant_id:
                raise AppError("CROSS_TENANT_ACCESS", "Tenant mismatch.", status_code=403)
            updated = SafetyGateResultRecord(
                id=r.id,
                tenant_id=r.tenant_id,
                campaign_id=r.campaign_id,
                contact_id=r.contact_id,
                draft_id=draft_id,
                gate_type=r.gate_type,
                status=r.status,
                severity=r.severity,
                reason_code=r.reason_code,
                safe_details=r.safe_details,
                created_at=r.created_at,
            )
            self.results[result_id] = updated
            return updated
        return None


class _FakeKnowledgeStore:
    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, KnowledgeDocumentRecord] = {}
        self.chunks: dict[uuid.UUID, KnowledgeChunkRecord] = {}

    async def create_document(
        self,
        *,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        source_url: str | None = None,
        status: str = "active",
    ) -> KnowledgeDocumentRecord:
        raise NotImplementedError()

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
        raise NotImplementedError()

    async def create_chunks(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: list[str],
    ) -> list[KnowledgeChunkRecord]:
        raise NotImplementedError()

    async def delete_chunks(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        raise NotImplementedError()

    async def list_chunks_for_grounding(
        self, *, tenant_id: uuid.UUID
    ) -> list[KnowledgeChunkRecord]:
        raise NotImplementedError()

    async def get_research_artifact_for_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Any | None:
        raise NotImplementedError()

    async def get_chunk(
        self, *, tenant_id: uuid.UUID, chunk_id: uuid.UUID
    ) -> KnowledgeChunkRecord | None:
        c = self.chunks.get(chunk_id)
        if c is not None and c.tenant_id == tenant_id:
            return c
        return None


class _FakeResearchStore:
    def __init__(self) -> None:
        self.artifacts: dict[uuid.UUID, ResearchArtifactRecord] = {}

    async def get_artifact(
        self, *, tenant_id: uuid.UUID, artifact_id: uuid.UUID
    ) -> ResearchArtifactRecord | None:
        art = self.artifacts.get(artifact_id)
        if art is not None and art.tenant_id == tenant_id:
            return art
        return None

    async def get_research_artifact_for_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ResearchArtifactRecord | None:
        return None


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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
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
        self.evidence.append(ev)
        return ev


@dataclass
class _Campaign:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str = "Test Campaign"


@dataclass
class _Contact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str = "contact@example.com"
    full_name: str = "John Doe"
    company_name: str = "CRE Corp"


class _FakeCampaignStore:
    async def get_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> _Campaign | None:
        if campaign_id == _CAMPAIGN:
            return _Campaign(id=campaign_id, tenant_id=tenant_id)
        return None


class _FakeContactStore:
    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> _Contact | None:
        if contact_id == _CONTACT:
            return _Contact(id=contact_id, tenant_id=tenant_id)
        return None


def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


# 1. Migration check
def test_migration_upgrades_check_constraint_to_include_groundedness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    # Constraint must drop and re-create to include 'groundedness'
    assert "DROP CONSTRAINT ck_safety_gate_results_gate_type" in sql
    assert (
        "gate_type IN ('prompt_injection', 'source_trust', 'groundedness')" in sql
        or "gate_type IN ('prompt_injection','source_trust','groundedness')" in sql.replace(" ", "")
    )


# 2. Groundedness gate validations
@pytest.mark.asyncio
async def test_groundedness_gate_evaluations() -> None:
    safety_store = _FakeSafetyStore()
    k_store = _FakeKnowledgeStore()
    r_store = _FakeResearchStore()
    service = GroundednessService(
        safety_store=safety_store,
        knowledge_store=k_store,
        research_store=r_store,
    )

    # Benign chunks & documents exist
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    k_store.documents[doc_id] = KnowledgeDocumentRecord(
        id=doc_id,
        tenant_id=_TENANT,
        title="Terms Document",
        source_url="https://cre.gov",
        content="Standard LTV parameters are defined here.",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        deleted_at=None,
    )
    k_store.chunks[chunk_id] = KnowledgeChunkRecord(
        id=chunk_id,
        tenant_id=_TENANT,
        document_id=doc_id,
        chunk_index=0,
        content="Standard LTV",
        created_at=datetime.now(UTC),
    )

    chunk = GroundingChunk(
        source_type="knowledge_chunk",
        source_id=chunk_id,
        content="Standard LTV",
        tenant_id=_TENANT,
    )

    # Valid claims pass
    res = await service.evaluate_draft_groundedness(
        principal=_principal(),
        subject="Intro to Acquisition",
        body="Acquisition terms look solid.",
        chunks=[chunk],
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )
    assert res.status == "passed"
    assert res.reason_code == "passed"

    # Empty chunks fail
    res_empty = await service.evaluate_draft_groundedness(
        principal=_principal(),
        subject="Intro to Acquisition",
        body="Acquisition terms look solid.",
        chunks=[],
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )
    assert res_empty.status == "failed"
    assert res_empty.reason_code == "no_evidence_provided"

    # Unsupported claims substring fail
    res_unsupported = await service.evaluate_draft_groundedness(
        principal=_principal(),
        subject="Intro to Acquisition",
        body="This is an unsupported claim.",
        chunks=[chunk],
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )
    assert res_unsupported.status == "failed"
    assert res_unsupported.reason_code == "unsupported_claims_detected"

    # Missing evidence chunk source fails
    missing_chunk = GroundingChunk(
        source_type="knowledge_chunk",
        source_id=uuid.uuid4(),
        content="Terms",
        tenant_id=_TENANT,
    )
    res_missing = await service.evaluate_draft_groundedness(
        principal=_principal(),
        subject="CRE Property Info",
        body="Solid terms.",
        chunks=[missing_chunk],
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )
    assert res_missing.status == "failed"
    assert res_missing.reason_code == "evidence_source_not_found"


# 3. Tenant isolation boundary test
@pytest.mark.asyncio
async def test_groundedness_cross_tenant_evidence_denied() -> None:
    safety_store = _FakeSafetyStore()
    k_store = _FakeKnowledgeStore()
    r_store = _FakeResearchStore()
    service = GroundednessService(
        safety_store=safety_store,
        knowledge_store=k_store,
        research_store=r_store,
    )

    # Chunk belongs to OTHER_TENANT
    cross_tenant_chunk = GroundingChunk(
        source_type="knowledge_chunk",
        source_id=uuid.uuid4(),
        content="Terms",
        tenant_id=_OTHER_TENANT,
    )

    with pytest.raises(AppError) as exc:
        await service.evaluate_draft_groundedness(
            principal=_principal(),
            subject="Terms",
            body="CRE acquisitions details",
            chunks=[cross_tenant_chunk],
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
        )
    assert exc.value.status_code == 403
    assert exc.value.code == "CROSS_TENANT_GROUNDING_SOURCE"


# 4. DraftGenerationService integration check (fails validation)
@pytest.mark.asyncio
async def test_draft_generation_integration_groundedness_fails() -> None:
    safety_store = _FakeSafetyStore()
    k_store = _FakeKnowledgeStore()
    r_store = _FakeResearchStore()

    # Grounding chunk exist but text content will contain unsupported claim
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    k_store.documents[doc_id] = KnowledgeDocumentRecord(
        id=doc_id,
        tenant_id=_TENANT,
        title="Terms Document",
        source_url="https://cre.gov",
        content="LTV defined",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        deleted_at=None,
    )
    k_store.chunks[chunk_id] = KnowledgeChunkRecord(
        id=chunk_id,
        tenant_id=_TENANT,
        document_id=doc_id,
        chunk_index=0,
        content="LTV defined",
        created_at=datetime.now(UTC),
    )

    class _MockGroundingService:
        async def retrieve_grounding_context(self, **kwargs: Any) -> GroundingContextResult:
            return GroundingContextResult(
                chunks=[
                    GroundingChunk(
                        source_type="knowledge_chunk",
                        source_id=chunk_id,
                        content="unsupported claim",  # triggers claims failure
                        tenant_id=_TENANT,
                    )
                ]
            )

    draft_store = _FakeDraftStore()
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    groundedness_service = GroundednessService(
        safety_store=safety_store,
        knowledge_store=k_store,
        research_store=r_store,
        audit_record=record_audit,
    )

    service = DraftGenerationService(
        draft_store=draft_store,
        campaign_store=_FakeCampaignStore(),
        contact_store=_FakeContactStore(),
        research_store=r_store,
        grounding_service=_MockGroundingService(),  # type: ignore
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        groundedness_service=groundedness_service,
        audit_record=record_audit,
    )

    res = await service.generate_draft(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        now=_NOW,
    )

    assert res.draft is not None
    assert res.draft.status == "needs_regeneration"
    assert "groundedness validation failure" in res.draft.body

    # Result saved in DB
    db_results = list(safety_store.results.values())
    g_res = next(r for r in db_results if r.gate_type == "groundedness")
    assert g_res.status == "failed"
    assert g_res.draft_id == res.draft.id

    # Minimized audit event details
    assert any(
        a["event_type"] == "safety.gate_failed" and a["details"]["gate_type"] == "groundedness"
        for a in audits
    )
    assert any(a["event_type"] == "draft.needs_regeneration" for a in audits)


# 5. Billing access check
@pytest.mark.asyncio
async def test_draft_generation_billing_gate_checked_before_groundedness() -> None:
    class _MockGroundingService:
        async def retrieve_grounding_context(self, **kwargs: Any) -> GroundingContextResult:
            raise AssertionError("Should not be called if billing denied")

    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    groundedness_service = GroundednessService(
        safety_store=safety_store,
        knowledge_store=_FakeKnowledgeStore(),
        research_store=_FakeResearchStore(),
    )

    service = DraftGenerationService(
        draft_store=draft_store,
        campaign_store=_FakeCampaignStore(),
        contact_store=_FakeContactStore(),
        research_store=_FakeResearchStore(),
        grounding_service=_MockGroundingService(),  # type: ignore
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=False)),  # denied
        groundedness_service=groundedness_service,
    )

    with pytest.raises(BillingAccessDenied):
        await service.generate_draft(
            principal=_principal(),
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            now=_NOW,
        )

    assert len(draft_store.drafts) == 0
    assert len(safety_store.results) == 0


# 6. Safety checks validation
@pytest.mark.asyncio
async def test_no_real_provider_calls_or_human_review_logic() -> None:
    import inspect

    source_code_g = inspect.getsource(GroundednessService)
    source_code_d = inspect.getsource(DraftGenerationService)

    # Assert no external/provider calls
    assert "openai" not in source_code_g.lower()
    assert "anthropic" not in source_code_g.lower()
    assert "cohere" not in source_code_g.lower()
    assert "scraping" not in source_code_g.lower()

    # Assert no human review paths
    assert "approve_draft" not in source_code_d.lower()
    assert "reject_draft" not in source_code_d.lower()
    assert "review_queue" not in source_code_d.lower()
