"""Tests for the local/mock-only grounding seed (P4-LocalDockerE2E-Fix-4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.config import Settings
from app.scripts.seed_local_grounding import (
    DEFAULT_TENANT_ID,
    SEED_DOC_CONTENT,
    SEED_DOC_TITLE,
    SeedEnvironmentError,
    build_seed_principal,
    ensure_seed_env_allowed,
    seed_grounding_document,
)
from app.services.authz import CAN_MANAGE_KNOWLEDGE, RBACService
from app.services.groundedness import GroundednessService
from app.services.rag_grounding import (
    GroundingChunk,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
)
from app.services.safety import SafetyGateResultRecord, SafetyService

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)

_BANNED_SUBSTRINGS = (
    "ignore previous instructions",
    "system prompt",
    "jailbreak",
    "unsupported claim",
    "hallucination",
    "fake claim",
)


def test_seed_refuses_non_local_envs() -> None:
    for env in ("staging", "production", "some-unknown-env"):
        with pytest.raises(SeedEnvironmentError):
            ensure_seed_env_allowed(Settings(app_env=env))


def test_seed_allows_local_mock_envs() -> None:
    for env in ("local", "development", "demo"):
        ensure_seed_env_allowed(Settings(app_env=env))


def test_seed_principal_is_local_mock_owner() -> None:
    principal = build_seed_principal(DEFAULT_TENANT_ID)
    assert principal.role == "owner"
    assert principal.tenant_id == DEFAULT_TENANT_ID
    assert RBACService().has_permission("owner", CAN_MANAGE_KNOWLEDGE) is True


def test_seed_content_has_no_gate_marker_strings() -> None:
    haystack = (SEED_DOC_TITLE + " " + SEED_DOC_CONTENT).lower()
    for term in _BANNED_SUBSTRINGS:
        assert term not in haystack


class _FakeKnowledgeStore:
    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, KnowledgeDocumentRecord] = {}
        self.chunks: dict[uuid.UUID, KnowledgeChunkRecord] = {}

    async def get_chunk(
        self, *, tenant_id: uuid.UUID, chunk_id: uuid.UUID
    ) -> KnowledgeChunkRecord | None:
        c = self.chunks.get(chunk_id)
        return c if c is not None and c.tenant_id == tenant_id else None

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


class _FakeCampaignStore:
    async def get_campaign(self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Any | None:
        raise AssertionError("add_document must not touch campaign_store")


class _FakeContactStore:
    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        raise AssertionError("add_document must not touch contact_store")


class _FakeBilling:
    async def require_feature(self, tenant_id: uuid.UUID, feature: str, *, now: datetime) -> None:
        raise AssertionError("add_document must not touch billing")


async def _build_grounding_service(k_store: _FakeKnowledgeStore) -> Any:
    from app.services.authz import ObjectAuthorizationService
    from app.services.rag_grounding import RAGGroundingService

    return RAGGroundingService(
        knowledge_store=k_store,
        campaign_store=_FakeCampaignStore(),
        contact_store=_FakeContactStore(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=_FakeBilling(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_seed_creates_document_and_chunks_once() -> None:
    k_store = _FakeKnowledgeStore()
    grounding = await _build_grounding_service(k_store)
    principal = build_seed_principal(_TENANT)

    first = await seed_grounding_document(
        knowledge_repo=k_store, grounding_service=grounding, principal=principal, now=_NOW
    )
    assert first.created is True
    assert first.chunk_count >= 1
    assert len(k_store.documents) == 1

    second = await seed_grounding_document(
        knowledge_repo=k_store, grounding_service=grounding, principal=principal, now=_NOW
    )
    assert second.created is False
    assert second.skipped_reason == "already_seeded"
    assert second.document_id == first.document_id
    assert len(k_store.documents) == 1


@pytest.mark.asyncio
async def test_seed_content_passes_safety_and_groundedness_gates() -> None:
    k_store = _FakeKnowledgeStore()
    grounding = await _build_grounding_service(k_store)
    principal = build_seed_principal(_TENANT)

    result = await seed_grounding_document(
        knowledge_repo=k_store, grounding_service=grounding, principal=principal, now=_NOW
    )
    chunks = await k_store.list_chunks_for_grounding(tenant_id=_TENANT)
    grounding_chunks = [
        GroundingChunk(
            source_type="knowledge_chunk",
            source_id=c.id,
            content=c.content,
            tenant_id=c.tenant_id,
        )
        for c in chunks
    ]

    class _FakeSafetyStore:
        def __init__(self) -> None:
            self.results: list[SafetyGateResultRecord] = []

        async def create_result(self, **kwargs: Any) -> SafetyGateResultRecord:
            rec = SafetyGateResultRecord(
                id=uuid.uuid4(),
                tenant_id=kwargs["tenant_id"],
                campaign_id=kwargs.get("campaign_id"),
                contact_id=kwargs.get("contact_id"),
                draft_id=kwargs.get("draft_id"),
                gate_type=kwargs["gate_type"],
                status=kwargs["status"],
                severity=kwargs["severity"],
                reason_code=kwargs["reason_code"],
                safe_details=kwargs["safe_details"],
                created_at=_NOW,
            )
            self.results.append(rec)
            return rec

    safety_store = _FakeSafetyStore()
    safety = SafetyService(safety_store=safety_store, knowledge_store=k_store)
    groundedness = GroundednessService(
        safety_store=safety_store, knowledge_store=k_store, research_store=k_store
    )

    safety_results = await safety.evaluate_grounding_safety(
        principal=principal, chunks=grounding_chunks
    )
    assert all(r.status == "passed" for r in safety_results)

    groundedness_result = await groundedness.evaluate_draft_groundedness(
        principal=principal,
        subject="Intro: Proposed CRE acquisition structure",
        body="Based on our guidelines: " + " ".join(c.content for c in chunks),
        chunks=grounding_chunks,
    )
    assert groundedness_result.status == "passed"
    assert result.created is True
