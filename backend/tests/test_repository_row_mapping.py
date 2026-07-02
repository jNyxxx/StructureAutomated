"""Regression tests for AsyncConnection repository row mapping.

These tests guard the local Docker E2E path against ``RETURNING(model).scalars()``
regressions, where asyncpg can surface the first scalar column instead of a full row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.audit.repository import AuditRepository
from app.repositories.billing_repo import BillingRepository
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.draft_repo import DraftEvidenceRecord, DraftRecord, DraftRepository
from app.repositories.followup_repo import (
    FollowUpRepository,
    FollowUpRuleRecord,
    FollowUpScheduleRecord,
)
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.membership_repo import MembershipRepository
from app.repositories.outcomes_repo import (
    OutcomeEventRecord,
    OutcomesRepository,
    ROIAssumptionsRecord,
)
from app.repositories.research_repo import ResearchRepository
from app.repositories.review_repo import ReviewRecord, ReviewRepository
from app.repositories.safety_repo import SafetyRepository
from app.repositories.sending_repo import (
    OutboundMessageRecord,
    SendGateResultRecord,
    SendingRepository,
)
from app.repositories.support_access_repo import SupportAccessRepository
from app.repositories.tenant_repo import TenantRepository
from app.repositories.user_repo import UserRepository
from app.services.auth import AuthMembership, AuthUser
from app.services.authz import SupportAccessGrant
from app.services.billing import BillingPlan, TenantSubscriptionRecord
from app.services.compliance import ComplianceProfileRecord, SuppressionRecord
from app.services.csv_import import ContactRecord
from app.services.rag_grounding import KnowledgeChunkRecord, KnowledgeDocumentRecord
from app.services.research import ResearchArtifactRecord, ResearchRunRecord
from app.services.safety import SafetyGateResultRecord
from app.services.settings_api import (
    AuditEventReadRecord,
    MembershipReadRecord,
    TenantSettingsRecord,
)

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
_PLAN = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_SUPPORT_GRANT = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_MEMBERSHIP = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
_USER = uuid.UUID("10101010-1010-1010-1010-101010101010")
_SUPPRESSION = uuid.UUID("20202020-2020-2020-2020-202020202020")
_SUPPRESSION_CURSOR = uuid.UUID("30303030-3030-3030-3030-303030303030")
_RULE = uuid.UUID("40404040-4040-4040-4040-404040404040")
_RULE_CURSOR = uuid.UUID("50505050-5050-5050-5050-505050505050")
_SCHEDULE = uuid.UUID("60606060-6060-6060-6060-606060606060")
_SCHEDULE_CURSOR = uuid.UUID("70707070-7070-7070-7070-707070707070")
_ORIG_OUTBOUND = uuid.UUID("80808080-8080-8080-8080-808080808080")
_ORIG_DRAFT = uuid.UUID("90909090-9090-9090-9090-909090909090")
_ACTOR = uuid.UUID("a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0")
_OUTCOME_EVENT = uuid.UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0")
_ROI = uuid.UUID("c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0")
_RESEARCH_RUN = uuid.UUID("d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0")
_RESEARCH_ARTIFACT = uuid.UUID("e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0")
_RESEARCH_CONTACT = uuid.UUID("f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0")
_TENANT_B = uuid.UUID("11111111-2222-3333-4444-555555555555")
_NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)


def _bound_params(statement: Any) -> dict[str, Any]:
    return statement.compile().params


def _where_sql(rendered_sql: str) -> str:
    return rendered_sql.split("WHERE", 1)[1] if "WHERE" in rendered_sql else ""


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


class _MappingListResult:
    """Like _MappingOnlyResult but wraps multiple rows — for the main-query
    leg of cursor pagination (``.mappings().all()``), or a "not found" lookup
    when given an empty list (``.first()`` returns None)."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.mappings_called = False

    def mappings(self) -> _MappingListResult:
        self.mappings_called = True
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def one(self) -> dict[str, Any]:
        return self.rows[0]

    def scalars(self) -> None:
        raise AssertionError("repositories must map complete rows, not scalar UUIDs")


class _SequencedRepositoryConnection:
    """Like _FakeRepositoryConnection, but returns a different canned result
    per sequential execute() call — for repository methods that issue two or
    more queries per call (nested lookups, cursor pagination). Clamps on the
    last supplied result if more calls occur than results were supplied."""

    def __init__(self, results: list[Any]) -> None:
        self._results = results
        self._call_index = 0
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> Any:
        self.statements.append(statement)
        result = self._results[self._call_index]
        if self._call_index < len(self._results) - 1:
            self._call_index += 1
        return result


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

    items, next_cursor = await repo.list_recent_bounded(tenant_id=_TENANT, cursor=None, limit=25)

    assert items == [AuditEventReadRecord(**row)]
    assert items[0].id == _AUDIT_EVENT
    assert next_cursor is None
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_audit_repository_list_recent_bounded_filters_by_tenant_id() -> None:
    """RLS defense-in-depth: audit_events is an RLS-only table (no app-level
    filter historically). This proves the repository scopes the query itself
    rather than relying solely on Postgres RLS, which local/dev/demo can
    bypass (BYPASSRLS role) -- see
    docs/evidence/phase-4-rls-defense-in-depth-fix.md."""
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

    await repo.list_recent_bounded(tenant_id=_TENANT, cursor=None, limit=25)

    stmt = conn.statements[0]
    where_sql = _where_sql(str(stmt))
    assert "audit_events.tenant_id" in where_sql
    assert _TENANT in _bound_params(stmt).values()


async def test_audit_repository_list_recent_bounded_scopes_to_given_tenant_not_hardcoded() -> None:
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

    await repo.list_recent_bounded(tenant_id=_TENANT_B, cursor=None, limit=25)

    stmt = conn.statements[0]
    bound = _bound_params(stmt).values()
    assert _TENANT_B in bound
    assert _TENANT not in bound


async def test_tenant_repository_get_current_tenant_returns_complete_row() -> None:
    row = {
        "id": _TENANT,
        "name": "Acme CRE",
        "status": "active",
        "settings": {},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = TenantRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_current_tenant(tenant_id=_TENANT)

    assert record == TenantSettingsRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_tenant_repository_get_current_tenant_filters_by_tenant_id() -> None:
    """See test_audit_repository_list_recent_bounded_filters_by_tenant_id docstring."""
    row = {
        "id": _TENANT,
        "name": "Acme CRE",
        "status": "active",
        "settings": {},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = TenantRepository(conn)  # type: ignore[arg-type]

    await repo.get_current_tenant(tenant_id=_TENANT)

    stmt = conn.statements[0]
    where_sql = _where_sql(str(stmt))
    assert "tenants.id" in where_sql
    assert _TENANT in _bound_params(stmt).values()


async def test_tenant_repository_get_current_tenant_scopes_to_given_tenant_not_hardcoded() -> None:
    row = {
        "id": _TENANT_B,
        "name": "Other Tenant",
        "status": "active",
        "settings": {},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = TenantRepository(conn)  # type: ignore[arg-type]

    await repo.get_current_tenant(tenant_id=_TENANT_B)

    stmt = conn.statements[0]
    bound = _bound_params(stmt).values()
    assert _TENANT_B in bound
    assert _TENANT not in bound


async def test_tenant_repository_update_current_tenant_returns_complete_row() -> None:
    row = {
        "id": _TENANT,
        "name": "Acme CRE Renamed",
        "status": "active",
        "settings": {"theme": "dark"},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = TenantRepository(conn)  # type: ignore[arg-type]

    record = await repo.update_current_tenant(
        tenant_id=_TENANT, name="Acme CRE Renamed", settings={"theme": "dark"}
    )

    assert record == TenantSettingsRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_tenant_repository_update_current_tenant_filters_by_tenant_id() -> None:
    row = {
        "id": _TENANT,
        "name": "Acme CRE Renamed",
        "status": "active",
        "settings": {"theme": "dark"},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = TenantRepository(conn)  # type: ignore[arg-type]

    await repo.update_current_tenant(
        tenant_id=_TENANT, name="Acme CRE Renamed", settings={"theme": "dark"}
    )

    stmt = conn.statements[0]
    where_sql = _where_sql(str(stmt))
    assert "tenants.id" in where_sql
    assert _TENANT in _bound_params(stmt).values()


async def test_tenant_repository_update_current_tenant_does_not_target_other_tenant() -> None:
    """An update scoped to tenant A can never carry tenant B's id in its WHERE
    clause bind parameters -- i.e. it cannot silently target another tenant's
    row even though Postgres RETURNING with no WHERE would previously have
    updated every tenant row in the table (see evidence doc)."""
    row = {
        "id": _TENANT,
        "name": "Acme CRE Renamed",
        "status": "active",
        "settings": {},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = TenantRepository(conn)  # type: ignore[arg-type]

    await repo.update_current_tenant(tenant_id=_TENANT, name="Acme CRE Renamed")

    stmt = conn.statements[0]
    assert _TENANT_B not in _bound_params(stmt).values()


async def test_support_access_repository_create_returns_complete_grant_row() -> None:
    row = {
        "id": _SUPPORT_GRANT,
        "tenant_id": _TENANT,
        "support_user_id": _ACTOR,
        "granted_by_user_id": _CONTACT,
        "reason": "Investigating ticket #123",
        "scope": "read_only",
        "expires_at": _NOW,
        "revoked_at": None,
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = SupportAccessRepository(conn)  # type: ignore[arg-type]

    created = await repo.create(
        tenant_id=_TENANT,
        support_user_id=_ACTOR,
        granted_by_user_id=_CONTACT,
        reason="Investigating ticket #123",
        scope="read_only",
        expires_at=_NOW,
        created_at=_NOW,
    )

    assert created == SupportAccessGrant(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_support_access_repository_get_active_returns_complete_grant_row() -> None:
    row = {
        "id": _SUPPORT_GRANT,
        "tenant_id": _TENANT,
        "support_user_id": _ACTOR,
        "granted_by_user_id": _CONTACT,
        "reason": "Investigating ticket #123",
        "scope": "read_only",
        "expires_at": _NOW,
        "revoked_at": None,
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = SupportAccessRepository(conn)  # type: ignore[arg-type]

    grant = await repo.get_active(
        tenant_id=_TENANT, support_user_id=_ACTOR, scope="read_only", now=_NOW
    )

    assert grant == SupportAccessGrant(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_support_access_repository_revoke_returns_complete_grant_row() -> None:
    row = {
        "id": _SUPPORT_GRANT,
        "tenant_id": _TENANT,
        "support_user_id": _ACTOR,
        "granted_by_user_id": _CONTACT,
        "reason": "Investigating ticket #123",
        "scope": "read_only",
        "expires_at": _NOW,
        "revoked_at": _NOW,
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = SupportAccessRepository(conn)  # type: ignore[arg-type]

    revoked = await repo.revoke(grant_id=_SUPPORT_GRANT, revoked_at=_NOW)

    assert revoked == SupportAccessGrant(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_membership_repository_list_memberships_returns_complete_rows() -> None:
    row = {
        "id": _MEMBERSHIP,
        "user_id": _ACTOR,
        "role": "owner",
        "membership_version": 1,
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = MembershipRepository(conn)  # type: ignore[arg-type]

    records = await repo.list_memberships()

    assert records == [MembershipReadRecord(**row)]
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_membership_repository_get_for_user_and_tenant_returns_auth_membership() -> None:
    row = {
        "tenant_id": _TENANT,
        "user_id": _ACTOR,
        "role": "owner",
        "membership_version": 1,
        "tenant_status": "active",
    }
    conn = _FakeRepositoryConnection(row)
    repo = MembershipRepository(conn)  # type: ignore[arg-type]

    membership = await repo.get_for_user_and_tenant(user_id=_ACTOR, tenant_id=_TENANT)

    assert membership == AuthMembership(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_user_repository_get_by_identity_returns_auth_user() -> None:
    row = {
        "id": _USER,
        "email": "owner@example.com",
        "identity_provider": "clerk",
        "provider_user_id": "provider-123",
        "deleted_at": None,
    }
    conn = _FakeRepositoryConnection(row)
    repo = UserRepository(conn)  # type: ignore[arg-type]

    user = await repo.get_by_identity(identity_provider="clerk", provider_user_id="provider-123")

    assert user == AuthUser(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_billing_repository_create_plan_returns_complete_plan_row() -> None:
    row = {
        "id": _PLAN,
        "key": "mvp_mock",
        "name": "MVP Mock Plan",
        "features": {"can_send": True},
    }
    conn = _FakeRepositoryConnection(row)
    repo = BillingRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_plan(
        key="mvp_mock", name="MVP Mock Plan", features={"can_send": True}
    )

    assert created == BillingPlan(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_billing_repository_set_status_returns_complete_subscription_and_plan() -> None:
    subscription_row = {
        "tenant_id": _TENANT,
        "plan_id": _PLAN,
        "tenant_status": "active",
        "grace_until": None,
    }
    plan_row = {
        "id": _PLAN,
        "key": "mvp_mock",
        "name": "MVP Mock Plan",
        "features": {"can_send": True},
    }
    conn = _SequencedRepositoryConnection(
        [_MappingOnlyResult(subscription_row), _MappingOnlyResult(plan_row)]
    )
    repo = BillingRepository(conn)  # type: ignore[arg-type]

    record = await repo.set_status(tenant_id=_TENANT, tenant_status="active", grace_until=None)

    assert record == TenantSubscriptionRecord(
        tenant_id=_TENANT,
        tenant_status="active",
        grace_until=None,
        plan=BillingPlan(**plan_row),
    )
    assert len(conn.statements) == 2


async def test_billing_repository_create_subscription_returns_complete_subscription_and_plan() -> (
    None
):
    subscription_row = {
        "tenant_id": _TENANT,
        "plan_id": _PLAN,
        "tenant_status": "active",
        "grace_until": None,
    }
    plan_row = {
        "id": _PLAN,
        "key": "mvp_mock",
        "name": "MVP Mock Plan",
        "features": {"can_send": True},
    }
    conn = _SequencedRepositoryConnection(
        [_MappingOnlyResult(subscription_row), _MappingOnlyResult(plan_row)]
    )
    repo = BillingRepository(conn)  # type: ignore[arg-type]

    record = await repo.create_subscription(
        tenant_id=_TENANT, plan_id=_PLAN, tenant_status="active"
    )

    assert record == TenantSubscriptionRecord(
        tenant_id=_TENANT,
        tenant_status="active",
        grace_until=None,
        plan=BillingPlan(**plan_row),
    )
    assert len(conn.statements) == 2


async def test_compliance_repository_get_profile_returns_complete_row() -> None:
    row = {
        "tenant_id": _TENANT,
        "jurisdiction": "US",
        "sending_review_required": True,
        "live_sending_allowed": False,
        "sms_allowed": False,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_profile(_TENANT)

    assert record == ComplianceProfileRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_compliance_repository_upsert_profile_insert_branch_returns_complete_row() -> None:
    new_row = {
        "tenant_id": _TENANT,
        "jurisdiction": "US",
        "sending_review_required": True,
        "live_sending_allowed": False,
        "sms_allowed": False,
    }
    conn = _SequencedRepositoryConnection([_MappingListResult([]), _MappingOnlyResult(new_row)])
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    record = await repo.upsert_profile(
        tenant_id=_TENANT,
        jurisdiction="US",
        sending_review_required=True,
        live_sending_allowed=False,
        sms_allowed=False,
    )

    assert record == ComplianceProfileRecord(**new_row)
    assert len(conn.statements) == 2


async def test_compliance_repository_upsert_profile_update_branch_returns_complete_row() -> None:
    existing_row = {
        "tenant_id": _TENANT,
        "jurisdiction": "US",
        "sending_review_required": False,
        "live_sending_allowed": False,
        "sms_allowed": False,
    }
    updated_row = {
        "tenant_id": _TENANT,
        "jurisdiction": "US",
        "sending_review_required": True,
        "live_sending_allowed": False,
        "sms_allowed": False,
    }
    conn = _SequencedRepositoryConnection(
        [_MappingOnlyResult(existing_row), _MappingOnlyResult(updated_row)]
    )
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    record = await repo.upsert_profile(
        tenant_id=_TENANT,
        jurisdiction="US",
        sending_review_required=True,
        live_sending_allowed=False,
        sms_allowed=False,
    )

    assert record == ComplianceProfileRecord(**updated_row)
    assert len(conn.statements) == 2


async def test_compliance_repository_get_active_suppression_returns_complete_row() -> None:
    row = {
        "id": _SUPPRESSION,
        "tenant_id": _TENANT,
        "channel": "email",
        "contact_hash": "hash123",
        "reason": "unsubscribed",
        "source": "manual",
        "never_contact": True,
        "created_at": _NOW,
        "revoked_at": None,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_active_suppression(
        tenant_id=_TENANT, channel="email", contact_hash="hash123"
    )

    assert record == SuppressionRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_compliance_repository_get_suppression_returns_complete_row() -> None:
    row = {
        "id": _SUPPRESSION,
        "tenant_id": _TENANT,
        "channel": "email",
        "contact_hash": "hash123",
        "reason": "unsubscribed",
        "source": "manual",
        "never_contact": True,
        "created_at": _NOW,
        "revoked_at": None,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_suppression(tenant_id=_TENANT, suppression_id=_SUPPRESSION)

    assert record == SuppressionRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_compliance_repository_list_suppressions_no_cursor_returns_complete_rows() -> None:
    row = {
        "id": _SUPPRESSION,
        "tenant_id": _TENANT,
        "channel": "email",
        "contact_hash": "hash123",
        "reason": "unsubscribed",
        "source": "manual",
        "never_contact": True,
        "created_at": _NOW,
        "revoked_at": None,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    records, next_cursor = await repo.list_suppressions(tenant_id=_TENANT, cursor=None, limit=25)

    assert records == [SuppressionRecord(**row)]
    assert next_cursor is None
    assert len(conn.statements) == 1


async def test_compliance_repository_list_suppressions_with_cursor_returns_complete_rows() -> None:
    cursor_row = {
        "id": _SUPPRESSION_CURSOR,
        "tenant_id": _TENANT,
        "channel": "email",
        "contact_hash": "hash-cursor",
        "reason": "unsubscribed",
        "source": "manual",
        "never_contact": True,
        "created_at": _NOW,
        "revoked_at": None,
    }
    page_row = {
        "id": _SUPPRESSION,
        "tenant_id": _TENANT,
        "channel": "email",
        "contact_hash": "hash123",
        "reason": "unsubscribed",
        "source": "manual",
        "never_contact": True,
        "created_at": _NOW,
        "revoked_at": None,
    }
    conn = _SequencedRepositoryConnection(
        [_MappingOnlyResult(cursor_row), _MappingListResult([page_row])]
    )
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    records, next_cursor = await repo.list_suppressions(
        tenant_id=_TENANT, cursor=str(_SUPPRESSION_CURSOR), limit=25
    )

    assert records == [SuppressionRecord(**page_row)]
    assert next_cursor is None
    assert len(conn.statements) == 2


async def test_compliance_repository_add_suppression_returns_complete_row() -> None:
    row = {
        "id": _SUPPRESSION,
        "tenant_id": _TENANT,
        "channel": "email",
        "contact_hash": "hash123",
        "reason": "unsubscribed",
        "source": "manual",
        "never_contact": True,
        "created_at": _NOW,
        "revoked_at": None,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    created = await repo.add_suppression(
        tenant_id=_TENANT,
        channel="email",
        contact_hash="hash123",
        reason="unsubscribed",
        source="manual",
        never_contact=True,
        created_at=_NOW,
    )

    assert created == SuppressionRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_compliance_repository_revoke_suppression_returns_complete_row() -> None:
    row = {
        "id": _SUPPRESSION,
        "tenant_id": _TENANT,
        "channel": "email",
        "contact_hash": "hash123",
        "reason": "unsubscribed",
        "source": "manual",
        "never_contact": True,
        "created_at": _NOW,
        "revoked_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ComplianceRepository(conn)  # type: ignore[arg-type]

    revoked = await repo.revoke_suppression(suppression_id=_SUPPRESSION, revoked_at=_NOW)

    assert revoked == SuppressionRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_followup_repository_create_rule_returns_complete_row() -> None:
    row = {
        "id": _RULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "delay_seconds": 86400,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_followup_rule(
        tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
    )

    assert created == FollowUpRuleRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_followup_repository_list_rules_no_cursor_returns_complete_rows() -> None:
    row = {
        "id": _RULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "delay_seconds": 86400,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    records, next_cursor = await repo.list_followup_rules(tenant_id=_TENANT, cursor=None, limit=25)

    assert records == [FollowUpRuleRecord(**row)]
    assert next_cursor is None
    assert len(conn.statements) == 1


async def test_followup_repository_list_rules_with_cursor_returns_complete_rows() -> None:
    cursor_row = {
        "id": _RULE_CURSOR,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "delay_seconds": 3600,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    page_row = {
        "id": _RULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "delay_seconds": 86400,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _SequencedRepositoryConnection(
        [_MappingOnlyResult(cursor_row), _MappingListResult([page_row])]
    )
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    records, next_cursor = await repo.list_followup_rules(
        tenant_id=_TENANT, cursor=str(_RULE_CURSOR), limit=25
    )

    assert records == [FollowUpRuleRecord(**page_row)]
    assert next_cursor is None
    assert len(conn.statements) == 2


async def test_followup_repository_get_rule_by_campaign_returns_complete_row() -> None:
    row = {
        "id": _RULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "delay_seconds": 86400,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_followup_rule_by_campaign(tenant_id=_TENANT, campaign_id=_CAMPAIGN)

    assert record == FollowUpRuleRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_followup_repository_create_schedule_returns_complete_row() -> None:
    row = {
        "id": _SCHEDULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "original_outbound_message_id": _ORIG_OUTBOUND,
        "original_draft_id": _ORIG_DRAFT,
        "followup_rule_id": _RULE,
        "status": "scheduled",
        "run_after": _NOW,
        "actor_user_id": _ACTOR,
        "actor_role": "system",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_followup_schedule(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        original_outbound_message_id=_ORIG_OUTBOUND,
        original_draft_id=_ORIG_DRAFT,
        followup_rule_id=_RULE,
        status="scheduled",
        run_after=_NOW,
        actor_user_id=_ACTOR,
        actor_role="system",
    )

    assert created == FollowUpScheduleRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_followup_repository_get_schedule_returns_complete_row() -> None:
    row = {
        "id": _SCHEDULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "original_outbound_message_id": _ORIG_OUTBOUND,
        "original_draft_id": _ORIG_DRAFT,
        "followup_rule_id": _RULE,
        "status": "scheduled",
        "run_after": _NOW,
        "actor_user_id": _ACTOR,
        "actor_role": "system",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_followup_schedule(tenant_id=_TENANT, schedule_id=_SCHEDULE)

    assert record == FollowUpScheduleRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_followup_repository_get_schedule_by_original_message_returns_complete_row() -> None:
    row = {
        "id": _SCHEDULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "original_outbound_message_id": _ORIG_OUTBOUND,
        "original_draft_id": _ORIG_DRAFT,
        "followup_rule_id": _RULE,
        "status": "scheduled",
        "run_after": _NOW,
        "actor_user_id": _ACTOR,
        "actor_role": "system",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_followup_schedule_by_original_message(
        tenant_id=_TENANT, original_outbound_message_id=_ORIG_OUTBOUND
    )

    assert record == FollowUpScheduleRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_followup_repository_list_schedules_no_cursor_returns_complete_rows() -> None:
    row = {
        "id": _SCHEDULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "original_outbound_message_id": _ORIG_OUTBOUND,
        "original_draft_id": _ORIG_DRAFT,
        "followup_rule_id": _RULE,
        "status": "scheduled",
        "run_after": _NOW,
        "actor_user_id": _ACTOR,
        "actor_role": "system",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    records, next_cursor = await repo.list_followup_schedules(
        tenant_id=_TENANT, cursor=None, limit=25
    )

    assert records == [FollowUpScheduleRecord(**row)]
    assert next_cursor is None
    assert len(conn.statements) == 1


async def test_followup_repository_list_schedules_with_cursor_returns_complete_rows() -> None:
    cursor_row = {
        "id": _SCHEDULE_CURSOR,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "original_outbound_message_id": _ORIG_OUTBOUND,
        "original_draft_id": _ORIG_DRAFT,
        "followup_rule_id": _RULE,
        "status": "sent",
        "run_after": _NOW,
        "actor_user_id": _ACTOR,
        "actor_role": "system",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    page_row = {
        "id": _SCHEDULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "original_outbound_message_id": _ORIG_OUTBOUND,
        "original_draft_id": _ORIG_DRAFT,
        "followup_rule_id": _RULE,
        "status": "scheduled",
        "run_after": _NOW,
        "actor_user_id": _ACTOR,
        "actor_role": "system",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _SequencedRepositoryConnection(
        [_MappingOnlyResult(cursor_row), _MappingListResult([page_row])]
    )
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    records, next_cursor = await repo.list_followup_schedules(
        tenant_id=_TENANT, cursor=str(_SCHEDULE_CURSOR), limit=25
    )

    assert records == [FollowUpScheduleRecord(**page_row)]
    assert next_cursor is None
    assert len(conn.statements) == 2


async def test_followup_repository_update_schedule_status_returns_complete_row() -> None:
    row = {
        "id": _SCHEDULE,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "original_outbound_message_id": _ORIG_OUTBOUND,
        "original_draft_id": _ORIG_DRAFT,
        "followup_rule_id": _RULE,
        "status": "sent",
        "run_after": _NOW,
        "actor_user_id": _ACTOR,
        "actor_role": "system",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = FollowUpRepository(conn)  # type: ignore[arg-type]

    updated = await repo.update_followup_schedule_status(
        tenant_id=_TENANT, schedule_id=_SCHEDULE, status="sent"
    )

    assert updated == FollowUpScheduleRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_outcomes_repository_get_outcome_event_returns_complete_row() -> None:
    row = {
        "id": _OUTCOME_EVENT,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "outbound_message_id": _OUTBOUND,
        "event_type": "reply_received",
        "note": None,
        "idempotency_key": None,
        "occurred_at": _NOW,
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = OutcomesRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_outcome_event(tenant_id=_TENANT, event_id=_OUTCOME_EVENT)

    assert record == OutcomeEventRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_outcomes_repository_get_by_idempotency_key_returns_complete_row() -> None:
    row = {
        "id": _OUTCOME_EVENT,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "contact_id": _CONTACT,
        "outbound_message_id": _OUTBOUND,
        "event_type": "reply_received",
        "note": None,
        "idempotency_key": "reply-key-1",
        "occurred_at": _NOW,
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = OutcomesRepository(conn)  # type: ignore[arg-type]

    record = await repo._get_by_idempotency_key(tenant_id=_TENANT, idempotency_key="reply-key-1")

    assert record == OutcomeEventRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_outcomes_repository_get_roi_assumptions_returns_complete_row() -> None:
    row = {
        "id": _ROI,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "cost_per_send_cents": 10,
        "pipeline_value_per_opportunity_cents": 500000,
        "revenue_per_deal_won_cents": 1000000,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = OutcomesRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_roi_assumptions(tenant_id=_TENANT, campaign_id=_CAMPAIGN)

    assert record == ROIAssumptionsRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_create_run_returns_complete_row() -> None:
    row = {
        "id": _RESEARCH_RUN,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "created_by_user_id": _ACTOR,
        "status": "queued",
        "queued_count": 1,
        "processed_count": 0,
        "failed_count": 0,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_run(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        created_by_user_id=_ACTOR,
        status="queued",
        queued_count=1,
    )

    assert created == ResearchRunRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_get_run_returns_complete_row() -> None:
    row = {
        "id": _RESEARCH_RUN,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "created_by_user_id": _ACTOR,
        "status": "queued",
        "queued_count": 1,
        "processed_count": 0,
        "failed_count": 0,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_run(tenant_id=_TENANT, run_id=_RESEARCH_RUN)

    assert record == ResearchRunRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_update_run_returns_complete_row() -> None:
    row = {
        "id": _RESEARCH_RUN,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "created_by_user_id": _ACTOR,
        "status": "completed",
        "queued_count": 1,
        "processed_count": 1,
        "failed_count": 0,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    record = await repo.update_run(tenant_id=_TENANT, run_id=_RESEARCH_RUN, status="completed")

    assert record == ResearchRunRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_increment_run_counts_returns_complete_row() -> None:
    row = {
        "id": _RESEARCH_RUN,
        "tenant_id": _TENANT,
        "campaign_id": _CAMPAIGN,
        "created_by_user_id": _ACTOR,
        "status": "queued",
        "queued_count": 1,
        "processed_count": 1,
        "failed_count": 0,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    record = await repo.increment_run_counts(tenant_id=_TENANT, run_id=_RESEARCH_RUN, processed=1)

    assert record == ResearchRunRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_create_artifact_returns_complete_row() -> None:
    row = {
        "id": _RESEARCH_ARTIFACT,
        "tenant_id": _TENANT,
        "research_run_id": _RESEARCH_RUN,
        "contact_id": _CONTACT,
        "findings": {"revenue": "10M"},
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    created = await repo.create_artifact(
        tenant_id=_TENANT,
        research_run_id=_RESEARCH_RUN,
        contact_id=_CONTACT,
        findings={"revenue": "10M"},
    )

    assert created == ResearchArtifactRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_get_artifact_returns_complete_row() -> None:
    row = {
        "id": _RESEARCH_ARTIFACT,
        "tenant_id": _TENANT,
        "research_run_id": _RESEARCH_RUN,
        "contact_id": _CONTACT,
        "findings": {"revenue": "10M"},
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_artifact(tenant_id=_TENANT, artifact_id=_RESEARCH_ARTIFACT)

    assert record == ResearchArtifactRecord(**row)
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_list_artifacts_returns_complete_rows() -> None:
    row = {
        "id": _RESEARCH_ARTIFACT,
        "tenant_id": _TENANT,
        "research_run_id": _RESEARCH_RUN,
        "contact_id": _CONTACT,
        "findings": {"revenue": "10M"},
        "created_at": _NOW,
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    records = await repo.list_artifacts(tenant_id=_TENANT, research_run_id=_RESEARCH_RUN)

    assert records == [ResearchArtifactRecord(**row)]
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1


async def test_research_repository_get_contact_returns_complete_contact_record() -> None:
    row = {
        "id": _RESEARCH_CONTACT,
        "tenant_id": _TENANT,
        "dedupe_hash": "hash-abc",
        "normalized_email": "john@crecorp.example",
        "normalized_domain": "crecorp.example",
        "normalized_company": "cre corp",
        "full_name": "John Cre",
        "title": "VP Acquisitions",
        "email": "john@crecorp.example",
        "domain": "crecorp.example",
        "company_name": "CRE Corp",
    }
    conn = _FakeRepositoryConnection(row)
    repo = ResearchRepository(conn)  # type: ignore[arg-type]

    record = await repo.get_contact(tenant_id=_TENANT, contact_id=_RESEARCH_CONTACT)

    assert record == ContactRecord(**row)
    assert record.email == "john@crecorp.example"
    assert record.full_name == "John Cre"
    assert record.company_name == "CRE Corp"
    assert conn.result.mappings_called is True
    assert len(conn.statements) == 1
