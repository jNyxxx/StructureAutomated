"""Tests for Phase 1 Slice P1-09 mock sending and send gates."""

from __future__ import annotations

import contextlib
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config

from app.auth.principal import CurrentPrincipal
from app.config import get_settings
from app.middleware.error_handler import AppError
from app.repositories.draft_repo import (
    DraftRecord,
)
from app.repositories.review_repo import ReviewRecord
from app.repositories.sending_repo import OutboundMessageRecord, SendGateResultRecord
from app.services.authz import (
    ObjectAuthorizationService,
    RBACService,
)
from app.services.billing import (
    BillingAccessDenied,
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)
from app.services.mock_sender import MockSenderService
from app.services.rate_limit import RateLimitPolicy
from app.services.safety import (
    SafetyGateResultRecord,
)
from app.services.send_gate import SendGateService

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
                features={"can_send": allowed},
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
        self.reviews: dict[uuid.UUID, ReviewRecord] = {}

    async def get_review_item_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> ReviewRecord | None:
        for r in self.reviews.values():
            if r.draft_id == draft_id and r.tenant_id == tenant_id:
                return r
        return None


class _FakeDraftStore:
    def __init__(self) -> None:
        self.drafts: dict[uuid.UUID, DraftRecord] = {}

    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> DraftRecord | None:
        d = self.drafts.get(draft_id)
        if d is not None and d.tenant_id == tenant_id:
            return d
        return None

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


@dataclass
class _Contact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str = "prospect@example.com"


class _FakeContactStore:
    def __init__(self) -> None:
        self.contact = _Contact(id=_CONTACT, tenant_id=_TENANT)

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> _Contact | None:
        if contact_id == self.contact.id and tenant_id == self.contact.tenant_id:
            return self.contact
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


class _FakeRateLimiter:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed

    async def check(
        self,
        policy: RateLimitPolicy,
        *,
        tenant_id: str | None = None,
        now: datetime,
    ) -> Any:
        @dataclass
        class Result:
            allowed: bool

        return Result(allowed=self.allowed)


def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


# 1. Migration check
def test_migration_sending_tables_and_rls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    assert "CREATE TABLE send_gate_results" in sql
    assert "CREATE TABLE outbound_messages" in sql
    assert "ALTER TABLE send_gate_results ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE outbound_messages FORCE ROW LEVEL SECURITY" in sql


# 2. Success sending approved draft
@pytest.mark.asyncio
async def test_send_approved_draft_success() -> None:
    sending_store = _FakeSendingStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()
    billing = BillingGateService(_BillingStore(allowed=True))
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    send_gate = SendGateService(
        sending_store=sending_store,
        draft_store=draft_store,
        review_store=review_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        compliance=compliance,
        audit_record=record_audit,
    )

    sender = MockSenderService(
        sending_store=sending_store,
        send_gate=send_gate,
        audit_record=record_audit,
    )

    # Setup draft
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro",
        body="Terms",
    )
    draft_store.drafts[draft.id] = draft

    # Setup review item approved
    review_item = ReviewRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
        reviewer_user_id=_ACTOR,
        action_reason=None,
        reviewed_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    review_store.reviews[review_item.id] = review_item

    # Setup safety results passed
    for gate in ("prompt_injection", "source_trust", "groundedness"):
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    res = await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert res.status == "mock_sent"
    assert res.sent_at == _NOW

    # Validate gate result passed
    assert len(sending_store.gate_results) == 1
    gate_res = list(sending_store.gate_results.values())[0]
    assert gate_res.status == "passed"
    assert gate_res.deny_reason_code is None

    # Validate outbound message recorded
    assert len(sending_store.outbound_messages) == 1
    outbound = list(sending_store.outbound_messages.values())[0]
    assert outbound.status == "mock_sent"

    # Validate audit events
    assert any(a["event_type"] == "send_gate.passed" for a in audits)
    assert any(a["event_type"] == "outbound_message.sent" for a in audits)


# 3. Gate evaluation denials
@pytest.mark.asyncio
async def test_send_gate_denial_cases() -> None:
    sending_store = _FakeSendingStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()
    billing_store = _BillingStore(allowed=True)
    billing = BillingGateService(billing_store)

    send_gate = SendGateService(
        sending_store=sending_store,
        draft_store=draft_store,
        review_store=review_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        compliance=compliance,
    )

    sender = MockSenderService(
        sending_store=sending_store,
        send_gate=send_gate,
    )

    # Setup draft
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro",
        body="Terms",
    )
    draft_store.drafts[draft.id] = draft

    # 1. Non-approved review denies
    review_item = ReviewRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="pending_review",
        reviewer_user_id=None,
        action_reason=None,
        reviewed_at=None,
        created_at=_NOW,
        updated_at=_NOW,
    )
    review_store.reviews[review_item.id] = review_item

    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "REVIEW_NOT_APPROVED"
    assert any(
        r.deny_reason_code == "review_not_approved" for r in sending_store.gate_results.values()
    )

    # Approve review
    review_store.reviews[review_item.id] = ReviewRecord(
        id=review_item.id,
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
        reviewer_user_id=_ACTOR,
        action_reason=None,
        reviewed_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )

    # 2. Missing safety results denies
    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_MISSING"

    # Populate safety results
    for gate in ("prompt_injection", "source_trust", "groundedness"):
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    # 3. Suppressed contact email denies
    compliance.suppressed_emails.add("prospect@example.com")
    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "COMPLIANCE_SUPPRESSED"
    compliance.suppressed_emails.clear()

    # 4. Failed safety check denies
    safety_store.results.clear()
    for gate in ("prompt_injection", "source_trust", "groundedness"):
        status = "failed" if gate == "prompt_injection" else "passed"
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status=status,
            severity="info",
            reason_code="failed",
            safe_details={},
            created_at=_NOW,
        )
    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "SAFETY_GATE_FAILED"

    # Restore passing safety results
    safety_store.results.clear()
    for gate in ("prompt_injection", "source_trust", "groundedness"):
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    # 5. Billing blocks denies
    billing_store.record = TenantSubscriptionRecord(
        tenant_id=_TENANT,
        tenant_status="active",
        plan=BillingPlan(
            id=_PLAN_ID,
            key="mvp_mock",
            name="MVP Mock",
            features={"can_send": False},
        ),
    )
    with pytest.raises(BillingAccessDenied):
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)

    # Restore billing
    billing_store.record = TenantSubscriptionRecord(
        tenant_id=_TENANT,
        tenant_status="active",
        plan=BillingPlan(
            id=_PLAN_ID,
            key="mvp_mock",
            name="MVP Mock",
            features={"can_send": True},
        ),
    )

    # 6. Mismatched review contact denies
    review_store.reviews.clear()
    mismatched_review = ReviewRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=uuid.uuid4(),
        status="approved",
        reviewer_user_id=_ACTOR,
        action_reason=None,
        reviewed_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    review_store.reviews[mismatched_review.id] = mismatched_review
    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert exc.value.status_code == 400
    assert exc.value.code == "DRAFT_MISMATCH"


# 4. Duplicate Send/Idempotency
@pytest.mark.asyncio
async def test_duplicate_send_blocks() -> None:
    sending_store = _FakeSendingStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))

    send_gate = SendGateService(
        sending_store=sending_store,
        draft_store=draft_store,
        review_store=review_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
    )

    sender = MockSenderService(
        sending_store=sending_store,
        send_gate=send_gate,
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro",
        body="Terms",
    )
    draft_store.drafts[draft.id] = draft

    review_item = ReviewRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
        reviewer_user_id=_ACTOR,
        action_reason=None,
        reviewed_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    review_store.reviews[review_item.id] = review_item

    for gate in ("prompt_injection", "source_trust", "groundedness"):
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    # Populate message in store beforehand
    await sending_store.create_outbound_message(
        tenant_id=_TENANT,
        draft_id=draft.id,
        status="mock_sent",
    )

    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert exc.value.status_code == 409
    assert exc.value.code == "DUPLICATE_SEND"


# 5. Throttling and Rate Limiting
@pytest.mark.asyncio
async def test_throttling_denies_send() -> None:
    sending_store = _FakeSendingStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))

    send_gate = SendGateService(
        sending_store=sending_store,
        draft_store=draft_store,
        review_store=review_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        rate_limiter=_FakeRateLimiter(allowed=False),  # type: ignore
        rate_limit_policy=RateLimitPolicy("risky", 1, timedelta(minutes=1)),
    )

    sender = MockSenderService(
        sending_store=sending_store,
        send_gate=send_gate,
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro",
        body="Terms",
    )
    draft_store.drafts[draft.id] = draft

    review_item = ReviewRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        draft_id=draft.id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
        reviewer_user_id=_ACTOR,
        action_reason=None,
        reviewed_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    review_store.reviews[review_item.id] = review_item

    for gate in ("prompt_injection", "source_trust", "groundedness"):
        safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="ok",
            safe_details={},
            created_at=_NOW,
        )

    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(_principal("owner"), draft_id=draft.id, now=_NOW)
    assert exc.value.status_code == 429
    assert exc.value.code == "RATE_LIMITED"


# 6. Tenant isolation and object auth boundaries
@pytest.mark.asyncio
async def test_cross_tenant_boundaries_isolated() -> None:
    sending_store = _FakeSendingStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    billing = BillingGateService(_BillingStore(allowed=True))

    send_gate = SendGateService(
        sending_store=sending_store,
        draft_store=draft_store,
        review_store=review_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
    )

    sender = MockSenderService(
        sending_store=sending_store,
        send_gate=send_gate,
    )

    # Draft belongs to OTHER_TENANT
    other_draft = await draft_store.create_draft(
        tenant_id=_OTHER_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Intro",
        body="Terms",
    )
    draft_store.drafts[other_draft.id] = other_draft

    with pytest.raises(AppError) as exc:
        await sender.send_approved_draft(
            _principal("owner", tenant_id=_TENANT), draft_id=other_draft.id, now=_NOW
        )
    assert exc.value.status_code in (403, 404)


# 7. No real provider libraries/scheduler checks
def test_no_real_providers_or_scheduler_accidentally_imported() -> None:
    import inspect

    from app.services.mock_sender import MockSenderService
    from app.services.send_gate import SendGateService

    source_sender = inspect.getsource(MockSenderService)
    source_gate = inspect.getsource(SendGateService)

    for src in (source_sender, source_gate):
        assert "smtp" not in src.lower()
        assert "twilio" not in src.lower()
        assert "sendgrid" not in src.lower()
        assert "mailgun" not in src.lower()
        assert "scheduler" not in src.lower()
