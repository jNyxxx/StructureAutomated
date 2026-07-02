"""Regression tests for AsyncConnection repository row mapping.

These tests guard the local Docker E2E path against ``RETURNING(model).scalars()``
regressions, where asyncpg can surface the first scalar column instead of a full row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.audit.repository import AuditRepository
from app.repositories.draft_repo import DraftEvidenceRecord, DraftRecord, DraftRepository
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.review_repo import ReviewRecord, ReviewRepository
from app.repositories.safety_repo import SafetyRepository
from app.repositories.sending_repo import (
    OutboundMessageRecord,
    SendGateResultRecord,
    SendingRepository,
)
from app.services.rag_grounding import KnowledgeChunkRecord, KnowledgeDocumentRecord
from app.services.safety import SafetyGateResultRecord
from app.services.settings_api import AuditEventReadRecord

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_CAMPAIGN = uuid.UUID("22222222-2222-2222-2222-222222222222")
_CONTACT = uuid.UUID("33333333-3333-3333-3333-333333333333")
_DRAFT = uuid.UUID("44444444-4444-4444-4444-444444444444")
_EVIDENCE = uuid.UUID("55555555-5555-5555-5555-555555555555")
_REVIEW = uuid.UUID("66666666-6666-6666-6666-666666666666")
_SAFETY = uuid.UUID("77777777-7777-7777-7777-777777777777")
_DOCUMENT = uuid.UUID("88888888-8888-8888-8888-888888888888")
_CHUNK = uuid.UUID("99999999-9999-9999-9999-999999999999")
_GATE_RESULT = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_OUTBOUND = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_AUDIT_EVENT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)


class _MappingOnlyResult:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row
        self.mappings_called = False

    def mappings(self) -> _MappingOnlyResult:
        self.mappings_called = True
        return self

    def one(self) -> dict[str, Any]:
        return self.row

    def first(self) -> dict[str, Any]:
        return self.row

    def all(self) -> list[dict[str, Any]]:
        return [self.row]

    def scalars(self) -> None:
        raise AssertionError("repositories must map complete rows, not scalar UUIDs")


class _FakeRepositoryConnection:
    def __init__(self, row: dict[str, Any]) -> None:
        self.result = _MappingOnlyResult(row)
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> _MappingOnlyResult:
        self.statements.append(statement)
        return self.result


async def test_draft_repository_create_returns_complete_draft_row() -> None:
    row = {
        "id": _DRAFT,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "status": "generated",
        "subject": "Subject",
        "body": "Body",
        "idempotency_key": "draft-key",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = DraftRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Subject",
        body="Body",
        idempotency_key="draft-key",
    )

    assert created == DraftRecord(**row)
    assert created.id == _DRAFT
    assert created.tenant_id == _TENANT
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_draft_repository_create_evidence_returns_complete_evidence_row() -> None:
    row = {
        "id": _EVIDENCE,
        "tenant_id": _TENANT,
        "draft_id": _DRAFT,
        "source_type": "knowledge_chunk",
        "source_id": uuid.UUID("88888888-8888-8888-8888-888888888888"),
        "content_snippet": "Grounded evidence snippet",
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = DraftRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_evidence(
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        source_type="knowledge_chunk",
        source_id=row["source_id"],
        content_snippet="Grounded evidence snippet",
    )

    assert created == DraftEvidenceRecord(**row)
    assert created.id == _EVIDENCE
    assert created.draft_id == _DRAFT
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_safety_repository_create_result_returns_complete_gate_row() -> None:
    row = {
        "id": _SAFETY,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "draft_id": None,
        "gate_type": "prompt_injection",
        "status": "passed",
        "severity": "info",
        "reason_code": "passed",
        "safe_details": {},
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = SafetyRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_result(
        tenant_id=_TENANT,
        gate_type="prompt_injection",
        status="passed",
        severity="info",
        reason_code="passed",
        safe_details={},
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    assert created == SafetyGateResultRecord(**row)
    assert created.id == _SAFETY
    assert created.tenant_id == _TENANT
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_review_repository_create_review_item_returns_complete_review_row() -> None:
    row = {
        "id": _REVIEW,
        "tenant_id": _TENANT,
        "draft_id": _DRAFT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "status": "pending_review",
        "reviewer_user_id": None,
        "action_reason": None,
        "reviewed_at": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ReviewRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_review_item(
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="pending_review",
    )

    assert created == ReviewRecord(**row)
    assert created.id == _REVIEW
    assert created.draft_id == _DRAFT
    assert created.status == "pending_review"
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_knowledge_repository_create_document_returns_complete_document_row() -> None:
    row = {
        "id": _DOCUMENT,
        "tenant_id": _TENANT,
        "title": "LOCAL DEMO MOCK - Grounding Guidelines",
        "source_url": None,
        "content": "LOCAL DEMO MOCK: deterministic grounding content.",
        "status": "active",
        "created_at": _NOW,
        "updated_at": _NOW,
        "deleted_at": None,
    }
    conn = _FakeRepositoryConnection(row)
    repo = KnowledgeRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_document(
        tenant_id=_TENANT,
        title=row["title"],
        content=row["content"],
    )

    assert created == KnowledgeDocumentRecord(**row)
    assert created.id == _DOCUMENT
    assert created.tenant_id == _TENANT
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_knowledge_repository_create_chunks_returns_complete_chunk_rows() -> None:
    row = {
        "id": _CHUNK,
        "tenant_id": _TENANT,
        "document_id": _DOCUMENT,
        "chunk_index": 0,
        "content": "LOCAL DEMO MOCK: deterministic grounding content.",
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = KnowledgeRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_chunks(
        tenant_id=_TENANT,
        document_id=_DOCUMENT,
        chunks=["LOCAL DEMO MOCK: deterministic grounding content."],
    )

    assert created == [KnowledgeChunkRecord(**row)]
    assert created[0].id == _CHUNK
    assert created[0].document_id == _DOCUMENT
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_sending_repository_create_gate_result_returns_complete_row() -> None:
    row = {
        "id": _GATE_RESULT,
        "tenant_id": _TENANT,
        "draft_id": _DRAFT,
        "status": "passed",
        "deny_reason_code": None,
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = SendingRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_gate_result(
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        status="passed",
    )

    assert created == SendGateResultRecord(**row)
    assert created.id == _GATE_RESULT
    assert created.draft_id == _DRAFT
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_sending_repository_create_outbound_message_returns_complete_row() -> None:
    row = {
        "id": _OUTBOUND,
        "tenant_id": _TENANT,
        "draft_id": _DRAFT,
        "status": "mock_sent",
        "sent_at": _NOW,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = SendingRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_outbound_message(
        tenant_id=_TENANT,
        draft_id=_DRAFT,
        status="mock_sent",
        sent_at=_NOW,
    )

    assert created == OutboundMessageRecord(**row)
    assert created.id == _OUTBOUND
    assert created.status == "mock_sent"
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_audit_repository_list_recent_bounded_returns_complete_rows() -> None:
    row = {
        "id": _AUDIT_EVENT,
        "event_type": "draft.generated",
        "actor_user_id": _CONTACT,
        "object_type": "draft",
        "object_id": _DRAFT,
        "request_id": None,
        "job_id": None,
        "redacted_details": {},
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = AuditRepository(conn)  # type: ignore[arg-type]

    items, next_cursor = await repo.list_recent_bounded(cursor=None, limit=25)

    assert items == [AuditEventReadRecord(**row)]
    assert items[0].id == _AUDIT_EVENT
    assert next_cursor is None
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1
