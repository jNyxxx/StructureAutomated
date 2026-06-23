"""Tests for Phase 1 Slice P1-08 human review queue."""

from __future__ import annotations

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
from app.services.rag_grounding import (
    GroundingContextResult,
)
from app.services.review import ReviewService
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


class _FakeReviewStore:
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, Any] = {}

    async def create_review_item(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str = "pending_review",
    ) -> Any:
        @dataclass
        class Item:
            id: uuid.UUID
            tenant_id: uuid.UUID
            draft_id: uuid.UUID
            campaign_id: uuid.UUID
            contact_id: uuid.UUID
            status: str
            reviewer_user_id: uuid.UUID | None
            action_reason: str | None
            reviewed_at: datetime | None
            created_at: datetime
            updated_at: datetime

        item = Item(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            draft_id=draft_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=status,
            reviewer_user_id=None,
            action_reason=None,
            reviewed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.items[item.id] = item
        return item

    async def get_review_item(self, *, tenant_id: uuid.UUID, review_id: uuid.UUID) -> Any | None:
        item = self.items.get(review_id)
        if item is not None and item.tenant_id == tenant_id:
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
    ) -> Any | None:
        item = self.items.get(review_id)
        if item is not None and item.tenant_id == tenant_id:
            item.status = status
            item.reviewer_user_id = reviewer_user_id
            item.action_reason = action_reason
            item.reviewed_at = reviewed_at
            item.updated_at = datetime.now(UTC)
            return item
        return None

    async def list_review_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[Any]:
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

    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> DraftRecord | None:
        draft = self.drafts.get(draft_id)
        if draft is not None and draft.tenant_id == tenant_id:
            return draft
        return None

    async def update_draft_status(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID, status: str
    ) -> DraftRecord | None:
        draft = self.drafts.get(draft_id)
        if draft is not None and draft.tenant_id == tenant_id:
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
                updated_at=datetime.now(UTC),
            )
            self.drafts[draft.id] = updated
            return updated
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


class _FakeSafetyStore:
    def __init__(self) -> None:
        self.results: dict[uuid.UUID, SafetyGateResultRecord] = {}

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

    async def update_result_draft_id(
        self, *, tenant_id: uuid.UUID, result_id: uuid.UUID, draft_id: uuid.UUID
    ) -> SafetyGateResultRecord | None:
        return None


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


def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


# 1. Migration check
def test_migration_review_table_and_rls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    assert "CREATE TABLE review_items" in sql
    assert "ALTER TABLE review_items ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE review_items FORCE ROW LEVEL SECURITY" in sql


# 2. RBAC gating tests
@pytest.mark.asyncio
async def test_list_review_queue_gated_by_rbac() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
    )

    # Put a draft in queue
    await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=uuid.uuid4(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    # Viewer has no permissions
    with pytest.raises(AppError) as exc:
        await service.list_review_queue(_principal("viewer"))
    assert exc.value.status_code == 403

    # Marketer and owner can view review queue
    res = await service.list_review_queue(_principal("marketer"))
    assert len(res) == 1


# 3. Approve draft flow
@pytest.mark.asyncio
async def test_approve_draft_flow() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()
    billing = BillingGateService(_BillingStore(allowed=True))
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        compliance=compliance,
        audit_record=record_audit,
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro subject",
        body="Body of email",
    )

    item = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    # Populate required safety results for the draft to allow approval
    for gate, status in [
        ("prompt_injection", "passed"),
        ("source_trust", "passed"),
        ("groundedness", "passed"),
    ]:
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status=status,
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    # Owner can approve draft
    updated_item = await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert updated_item.status == "approved"
    assert updated_item.reviewer_user_id == _ACTOR
    assert updated_item.reviewed_at == _NOW

    # Audit log emitted
    assert len(audits) == 1
    assert audits[0]["event_type"] == "draft.approved"
    assert audits[0]["details"]["draft_id"] == str(draft.id)


@pytest.mark.asyncio
async def test_approve_valid_draft_with_source_trust_warning() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()
    billing = BillingGateService(_BillingStore(allowed=True))

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        compliance=compliance,
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro subject",
        body="Body of email",
    )

    item = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    # Source trust is warning (allowed), other gates pass
    for gate, status in [
        ("prompt_injection", "passed"),
        ("source_trust", "warning"),
        ("groundedness", "passed"),
    ]:
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status=status,
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    updated_item = await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert updated_item.status == "approved"


@pytest.mark.asyncio
async def test_approve_draft_denies_missing_or_failed_gates() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro subject",
        body="Body of email",
    )

    item = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    def set_results(gates_list):
        safety_store.results.clear()
        for gate, status in gates_list:
            safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
                id=uuid.uuid4(),
                tenant_id=_TENANT,
                campaign_id=_CAMPAIGN,
                contact_id=_CONTACT,
                draft_id=draft.id,
                gate_type=gate,
                status=status,
                severity="info",
                reason_code="ok",
                safe_details={},
                created_at=_NOW,
            )

    # 1. Missing prompt_injection
    set_results([("source_trust", "passed"), ("groundedness", "passed")])
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_MISSING"

    # 2. Missing source_trust
    set_results([("prompt_injection", "passed"), ("groundedness", "passed")])
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_MISSING"

    # 3. Missing groundedness
    set_results([("prompt_injection", "passed"), ("source_trust", "passed")])
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_MISSING"

    # 4. Failed prompt_injection
    set_results(
        [("prompt_injection", "failed"), ("source_trust", "passed"), ("groundedness", "passed")]
    )
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_FAILED"

    # 5. Failed source_trust
    set_results(
        [("prompt_injection", "passed"), ("source_trust", "failed"), ("groundedness", "passed")]
    )
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_FAILED"

    # 6. Failed groundedness
    set_results(
        [("prompt_injection", "passed"), ("source_trust", "passed"), ("groundedness", "failed")]
    )
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_FAILED"

    # 7. Groundedness warning is denied (must pass)
    set_results(
        [("prompt_injection", "passed"), ("source_trust", "passed"), ("groundedness", "warning")]
    )
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_FAILED"


@pytest.mark.asyncio
async def test_approve_draft_failures() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()
    billing = BillingGateService(_BillingStore(allowed=True))

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        compliance=compliance,
    )

    # 1. Non-approve permission (Marketer has review but not approve)
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Subject",
        body="Body",
    )
    item = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("marketer"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 403

    # Populate valid gates for subsequent tests
    for gate, status in [
        ("prompt_injection", "passed"),
        ("source_trust", "passed"),
        ("groundedness", "passed"),
    ]:
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status=status,
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    # 2. Blocked status draft cannot be approved
    blocked_draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="blocked",
        subject="Blocked Draft",
        body="Blocked",
    )
    blocked_item = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=blocked_draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=blocked_item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert "INVALID_DRAFT_STATE" in exc.value.code

    # 3. Suppressed contact draft cannot be approved
    compliance.suppressed_emails.add("contact@example.com")
    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert "COMPLIANCE_SUPPRESSED" in exc.value.code

    # Remove suppression
    compliance.suppressed_emails.clear()


# 4. Reject and Request Regeneration
@pytest.mark.asyncio
async def test_reject_and_request_regeneration() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        audit_record=record_audit,
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro subject",
        body="Body of email",
    )

    item1 = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )
    item2 = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    # 1. Reject draft
    rejected = await service.reject_draft(
        _principal("marketer"), review_id=item1.id, reason="Bad tone", now=_NOW
    )
    assert rejected.status == "rejected"
    assert rejected.action_reason == "Bad tone"
    assert any(a["event_type"] == "draft.rejected" for a in audits)

    # 2. Request regeneration
    regenerate = await service.request_regeneration(
        _principal("marketer"), review_id=item2.id, reason="Missing terms", now=_NOW
    )
    assert regenerate.status == "regeneration_requested"
    assert regenerate.action_reason == "Missing terms"
    assert any(a["event_type"] == "draft.needs_regeneration" for a in audits)

    # Draft status must be updated to needs_regeneration
    updated_draft = await draft_store.get_draft(tenant_id=_TENANT, draft_id=draft.id)
    assert updated_draft is not None
    assert updated_draft.status == "needs_regeneration"


# 5. Tenant boundary isolation checks
@pytest.mark.asyncio
async def test_tenant_boundary_isolation_checks() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
    )

    # Create draft and review item for OTHER_TENANT
    other_draft = await draft_store.create_draft(
        tenant_id=_OTHER_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro",
        body="Body",
    )
    other_item = await review_store.create_review_item(
        tenant_id=_OTHER_TENANT,
        draft_id=other_draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    # Accessing OTHER_TENANT's item under _TENANT principal is denied.
    # It should return 404 because scoped lookup fails or 403.
    with pytest.raises(AppError) as exc:
        await service.approve_draft(
            _principal("owner", tenant_id=_TENANT), review_id=other_item.id, now=_NOW
        )
    assert exc.value.status_code in (403, 404)


# 6. DraftGenerationService automatically queues draft
@pytest.mark.asyncio
async def test_draft_generation_auto_queues_pending_review() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    k_store = _FakeContactStore()
    r_store = _FakeCampaignStore()

    class _MockGroundingService:
        async def retrieve_grounding_context(self, **kwargs: Any) -> GroundingContextResult:
            return GroundingContextResult(chunks=[])

    service = DraftGenerationService(
        draft_store=draft_store,
        campaign_store=r_store,
        contact_store=k_store,
        research_store=None,  # type: ignore
        grounding_service=_MockGroundingService(),  # type: ignore
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        review_store=review_store,
    )

    res = await service.generate_draft(
        principal=_principal(),
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        now=_NOW,
    )

    assert res.draft is not None
    assert res.draft.status == "generated"

    # Queue must have a review item in pending_review
    queue = await review_store.list_review_queue(tenant_id=_TENANT)
    assert len(queue) == 1
    assert queue[0].draft_id == res.draft.id
    assert queue[0].status == "pending_review"


# 7. Billing check on request_regeneration and approve_draft
@pytest.mark.asyncio
async def test_billing_denied_blocks_review_actions() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=False))

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro subject",
        body="Body of email",
    )

    item = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
    )

    # Approval blocked
    with pytest.raises(BillingAccessDenied):
        await service.approve_draft(_principal("owner"), review_id=item.id, now=_NOW)

    # Regeneration request blocked
    with pytest.raises(BillingAccessDenied):
        await service.request_regeneration(_principal("owner"), review_id=item.id, now=_NOW)


# 8. Mismatch validation checks
@pytest.mark.asyncio
async def test_review_item_draft_mismatch_denies_approval() -> None:
    review_store = _FakeReviewStore()
    draft_store = _FakeDraftStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))

    service = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Subject",
        body="Body",
    )

    mismatched_item = await review_store.create_review_item(
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=uuid.uuid4(),
    )

    with pytest.raises(AppError) as exc:
        await service.approve_draft(_principal("owner"), review_id=mismatched_item.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "DRAFT_MISMATCH"


# 9. Ensure no sending logic is present in ReviewService
def test_no_sending_accidentally_added() -> None:
    import inspect

    from app.services.review import ReviewService

    source_code = inspect.getsource(ReviewService)
    assert "smtp" not in source_code.lower()
    assert "ses" not in source_code.lower()
    assert "mailgun" not in source_code.lower()
    assert "send_email" not in source_code.lower()
