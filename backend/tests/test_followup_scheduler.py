"""Tests for Phase 1 Slice P1-10 mock follow-up scheduler and outbox queue integration."""

from __future__ import annotations

import contextlib
import io
import uuid
from collections.abc import Callable
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
from app.models.job import JobStatus
from app.repositories.followup_repo import FollowUpRuleRecord, FollowUpScheduleRecord
from app.services.authz import (
    ObjectAuthorizationService,
    RBACService,
)
from app.services.billing import (
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)
from app.services.followup_scheduler import FollowUpSchedulerService
from app.services.mock_sender import MockSenderService
from app.services.queue import JobRecord, QueueService
from app.services.safety import SafetyGateResultRecord
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


def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", "postgresql://mock_url")
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


# 1. Migration check
def test_migration_followup_tables_and_rls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    assert "CREATE TABLE followup_rules" in sql
    assert "CREATE TABLE followup_schedules" in sql
    assert "ALTER TABLE followup_rules ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE followup_schedules FORCE ROW LEVEL SECURITY" in sql


# Fakes and Mocks
class _FakeBillingStore:
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

    async def set_status(self, **kwargs: Any) -> Any:
        raise AssertionError("not used")


class _FakeFollowUpStore:
    def __init__(self) -> None:
        self.rules: dict[uuid.UUID, FollowUpRuleRecord] = {}
        self.schedules: dict[uuid.UUID, FollowUpScheduleRecord] = {}

    async def create_followup_rule(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        delay_seconds: int,
    ) -> FollowUpRuleRecord:
        rule = FollowUpRuleRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            delay_seconds=delay_seconds,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.rules[rule.id] = rule
        return rule

    async def get_followup_rule_by_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> FollowUpRuleRecord | None:
        for r in self.rules.values():
            if r.tenant_id == tenant_id and r.campaign_id == campaign_id:
                return r
        return None

    async def create_followup_schedule(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        original_outbound_message_id: uuid.UUID,
        original_draft_id: uuid.UUID,
        followup_rule_id: uuid.UUID,
        status: str,
        run_after: datetime,
        actor_user_id: uuid.UUID,
        actor_role: str,
    ) -> FollowUpScheduleRecord:
        schedule = FollowUpScheduleRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            original_outbound_message_id=original_outbound_message_id,
            original_draft_id=original_draft_id,
            followup_rule_id=followup_rule_id,
            status=status,
            run_after=run_after,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.schedules[schedule.id] = schedule
        return schedule

    async def get_followup_schedule(
        self, *, tenant_id: uuid.UUID, schedule_id: uuid.UUID
    ) -> FollowUpScheduleRecord | None:
        s = self.schedules.get(schedule_id)
        if s is not None and s.tenant_id == tenant_id:
            return s
        return None

    async def get_followup_schedule_by_original_message(
        self, *, tenant_id: uuid.UUID, original_outbound_message_id: uuid.UUID
    ) -> FollowUpScheduleRecord | None:
        for s in self.schedules.values():
            if (
                s.tenant_id == tenant_id
                and s.original_outbound_message_id == original_outbound_message_id
            ):
                return s
        return None

    async def update_followup_schedule_status(
        self,
        *,
        tenant_id: uuid.UUID,
        schedule_id: uuid.UUID,
        status: str,
    ) -> FollowUpScheduleRecord | None:
        s = self.schedules.get(schedule_id)
        if s is not None and s.tenant_id == tenant_id:
            from dataclasses import replace

            updated = replace(s, status=status, updated_at=_NOW)
            self.schedules[schedule_id] = updated
            return updated
        return None


@dataclass(frozen=True)
class _FakeCampaign:
    id: uuid.UUID
    tenant_id: uuid.UUID


class _FakeCampaignStore:
    def __init__(self) -> None:
        self.campaigns: dict[uuid.UUID, _FakeCampaign] = {}

    async def get_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> _FakeCampaign | None:
        c = self.campaigns.get(campaign_id)
        if c is not None and c.tenant_id == tenant_id:
            return c
        return None


@dataclass(frozen=True)
class _FakeDraft:
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str


class _FakeDraftStore:
    def __init__(self) -> None:
        self.drafts: dict[uuid.UUID, _FakeDraft] = {}

    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> _FakeDraft | None:
        d = self.drafts.get(draft_id)
        if d is not None and d.tenant_id == tenant_id:
            return d
        return None


@dataclass(frozen=True)
class _FakeOutboundMessage:
    id: uuid.UUID
    tenant_id: uuid.UUID
    draft_id: uuid.UUID
    status: str
    sent_at: datetime | None


class _FakeSendingStore:
    def __init__(self) -> None:
        self.messages: dict[uuid.UUID, _FakeOutboundMessage] = {}
        self.gate_results: list[dict[str, Any]] = []

    async def create_gate_result(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        deny_reason_code: str | None = None,
    ) -> Any:
        res = {
            "tenant_id": tenant_id,
            "draft_id": draft_id,
            "status": status,
            "deny_reason_code": deny_reason_code,
        }
        self.gate_results.append(res)
        return res

    async def get_outbound_message_by_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> _FakeOutboundMessage | None:
        for m in self.messages.values():
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
    ) -> _FakeOutboundMessage:
        msg = _FakeOutboundMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            draft_id=draft_id,
            status=status,
            sent_at=sent_at,
        )
        self.messages[msg.id] = msg
        return msg


class _FakeQueueRepo:
    def __init__(self) -> None:
        self.jobs: dict[uuid.UUID, JobRecord] = {}

    async def get_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, idempotency_key: str
    ) -> JobRecord | None:
        for r in self.jobs.values():
            if r.tenant_id == tenant_id and r.idempotency_key == idempotency_key:
                return r
        return None

    async def insert(self, job: JobRecord) -> None:
        self.jobs[job.id] = job

    async def claim_next(self, *, now: datetime, lease: timedelta) -> JobRecord | None:
        for r in self.jobs.values():
            if r.status == JobStatus.QUEUED and r.run_after <= now:
                return r
        return None

    async def update(self, *, job_id: uuid.UUID, fields: dict[str, Any]) -> None:
        from dataclasses import replace

        if job_id in self.jobs:
            self.jobs[job_id] = replace(self.jobs[job_id], **fields)


@dataclass(frozen=True)
class _FakeReviewItem:
    tenant_id: uuid.UUID
    draft_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str


class _FakeReviewStore:
    def __init__(self) -> None:
        self.reviews: dict[uuid.UUID, _FakeReviewItem] = {}

    async def get_review_item_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> _FakeReviewItem | None:
        for r in self.reviews.values():
            if r.draft_id == draft_id and r.tenant_id == tenant_id:
                return r
        return None


class _FakeSafetyStore:
    def __init__(self) -> None:
        self.results: dict[uuid.UUID, SafetyGateResultRecord] = {}

    async def list_results_for_context(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID | None = None,
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
    ) -> list[SafetyGateResultRecord]:
        return [
            r for r in self.results.values() if r.tenant_id == tenant_id and r.draft_id == draft_id
        ]


@dataclass(frozen=True)
class _FakeContact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str


class _FakeContactStore:
    def __init__(self) -> None:
        self.contacts: dict[uuid.UUID, _FakeContact] = {}

    async def get_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> _FakeContact | None:
        c = self.contacts.get(contact_id)
        if c is not None and c.tenant_id == tenant_id:
            return c
        return None


class _FakeCompliance:
    def __init__(self, suppressed_identifiers: set[str] | None = None) -> None:
        self.suppressed = suppressed_identifiers or set()

    async def is_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> bool:
        return contact_identifier in self.suppressed

    async def get_active_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
    ) -> Any | None:
        from app.services.compliance import hash_contact_identifier

        for identifier in self.suppressed:
            h = hash_contact_identifier(channel=channel, contact_identifier=identifier)
            if h == contact_hash:

                class DummySuppression:
                    pass

                return DummySuppression()
        return None


@contextlib.asynccontextmanager
async def _dummy_claim_context() -> Any:
    yield object()


@contextlib.asynccontextmanager
async def _dummy_tenant_context(tenant_id: uuid.UUID) -> Any:
    yield object()


# 2. Test Rule Creation
@pytest.mark.asyncio
async def test_create_followup_rule() -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))

    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
    )

    # Success
    rule = await service.create_followup_rule(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        delay_seconds=86400,
    )
    assert rule.campaign_id == _CAMPAIGN
    assert rule.delay_seconds == 86400

    # Duplicate denied
    with pytest.raises(AppError) as exc:
        await service.create_followup_rule(
            _principal("owner"),
            campaign_id=_CAMPAIGN,
            delay_seconds=86400,
        )
    assert exc.value.code == "DUPLICATE_RULE"

    # Invalid delay
    with pytest.raises(AppError) as exc:
        await service.create_followup_rule(
            _principal("owner"),
            campaign_id=_CAMPAIGN,
            delay_seconds=0,
        )
    assert exc.value.code == "INVALID_DELAY"

    # RBAC Denied
    with pytest.raises(AppError) as exc:
        await service.create_followup_rule(
            _principal("viewer"),
            campaign_id=_CAMPAIGN,
            delay_seconds=3600,
        )
    assert exc.value.code == "FORBIDDEN"


# 3. Test Auto Scheduling after Message Sent
@pytest.mark.asyncio
async def test_auto_schedule_after_sending() -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    sending_store = _FakeSendingStore()
    review_store = _FakeReviewStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    scheduler = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
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
        object_authz=obj_authz,
        compliance=compliance,
    )

    sender = MockSenderService(
        sending_store=sending_store,
        send_gate=send_gate,
        followups=scheduler,
        audit_record=record_audit,
    )

    # Setup follow-up rule
    await store.create_followup_rule(tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400)

    # Setup Draft and gates to allow mock send
    draft_id = uuid.uuid4()
    draft_store.drafts[draft_id] = _FakeDraft(
        id=draft_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
    )
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="c@test.com"
    )
    review_store.reviews[uuid.uuid4()] = _FakeReviewItem(
        tenant_id=_TENANT,
        draft_id=draft_id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
    )
    safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="prompt_injection",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="source_trust",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="groundedness",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )

    # Act: Perform send approved draft which should automatically schedule follow-up
    res = await sender.send_approved_draft(
        principal=_principal("owner"),
        draft_id=draft_id,
        now=_NOW,
    )

    # Verify followup schedule exists with status queued
    schedule = await store.get_followup_schedule_by_original_message(
        tenant_id=_TENANT, original_outbound_message_id=res.outbound_message_id
    )
    assert schedule is not None
    assert schedule.status == "queued"
    assert schedule.run_after == _NOW + timedelta(seconds=86400)

    # Verify job enqueued in QueueService outbox
    assert isinstance(queue._repo, _FakeQueueRepo)
    queued_jobs = list(queue._repo.jobs.values())
    assert len(queued_jobs) == 1
    assert queued_jobs[0].job_type == "send_followup"
    assert queued_jobs[0].payload["followup_schedule_id"] == str(schedule.id)
    assert queued_jobs[0].run_after == _NOW + timedelta(seconds=86400)

    # Verify audit event followup.scheduled was logged
    scheduled_audits = [a for a in audits if a["event_type"] == "followup.scheduled"]
    assert len(scheduled_audits) == 1


# 4. Test Background Process Job Success
@pytest.mark.asyncio
async def test_process_job_success(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
        audit_record=record_audit,
    )

    # We mock the factory function to return our in-memory fake store in background execution
    service._followup_repo_factory = lambda c: store

    rule = await store.create_followup_rule(
        tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
    )
    original_msg_id = uuid.uuid4()
    draft_id = uuid.uuid4()

    # Create schedule in queued state
    schedule = await store.create_followup_schedule(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        original_outbound_message_id=original_msg_id,
        original_draft_id=draft_id,
        followup_rule_id=rule.id,
        status="queued",
        run_after=_NOW + timedelta(seconds=86400),
        actor_user_id=_ACTOR,
        actor_role="owner",
    )

    # Setup database mocks (mocking the repositories that process_job imports from conn)
    # We monkeypatch the repositories to use our fakes
    import app.repositories.billing_repo
    import app.repositories.compliance_repo
    import app.repositories.draft_repo
    import app.repositories.review_repo
    import app.repositories.safety_repo
    import app.repositories.sending_repo

    fake_draft_repo = _FakeDraftStore()
    fake_sending_repo = _FakeSendingStore()
    fake_review_repo = _FakeReviewStore()
    fake_safety_repo = _FakeSafetyStore()
    fake_billing_repo = _FakeBillingStore(allowed=True)
    fake_compliance_repo = _FakeCompliance()

    fake_draft_repo.drafts[draft_id] = _FakeDraft(
        id=draft_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
    )
    fake_sending_repo.messages[original_msg_id] = _FakeOutboundMessage(
        id=original_msg_id,
        tenant_id=_TENANT,
        draft_id=draft_id,
        status="mock_sent",
        sent_at=_NOW,
    )
    fake_review_repo.reviews[uuid.uuid4()] = _FakeReviewItem(
        tenant_id=_TENANT,
        draft_id=draft_id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
    )
    fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="prompt_injection",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="source_trust",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="groundedness",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )

    # Monkeypatch the database ORM classes to return these fake repositories
    monkeypatch.setattr(app.repositories.draft_repo, "DraftRepository", lambda c: fake_draft_repo)
    monkeypatch.setattr(
        app.repositories.sending_repo, "SendingRepository", lambda c: fake_sending_repo
    )
    monkeypatch.setattr(
        app.repositories.review_repo, "ReviewRepository", lambda c: fake_review_repo
    )
    monkeypatch.setattr(
        app.repositories.safety_repo, "SafetyRepository", lambda c: fake_safety_repo
    )
    monkeypatch.setattr(
        app.repositories.billing_repo, "BillingRepository", lambda c: fake_billing_repo
    )
    monkeypatch.setattr(
        app.repositories.compliance_repo, "ComplianceRepository", lambda c: fake_compliance_repo
    )

    # Mock Contact model import in process_job
    class DummyContact:
        def __init__(self) -> None:
            self.id = _CONTACT
            self.tenant_id = _TENANT
            self.email = "c@test.com"

    class DummyConn:
        async def execute(self, *args: Any, **kwargs: Any) -> Any:
            class DummyResult:
                def scalars(self) -> Any:
                    class DummyScalars:
                        def first(self) -> Any:
                            return DummyContact()

                    return DummyScalars()

            return DummyResult()

    job = JobRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        job_type="send_followup",
        payload={"followup_schedule_id": str(schedule.id)},
        status=JobStatus.QUEUED,
        attempts=0,
        max_attempts=3,
        run_after=_NOW + timedelta(seconds=86400),
        locked_until=None,
        idempotency_key="key_1",
        last_error=None,
    )

    # Act: Process job
    await service.process_job(job, DummyConn())

    # Assert: Verify schedule updated to mock_sent
    assert store.schedules[schedule.id].status == "mock_sent"

    # Assert: Verify audit event emitted
    sent_audits = [a for a in audits if a["event_type"] == "followup.mock_sent"]
    assert len(sent_audits) == 1


# 5. Test Background Process Job Skipped by Compliance
@pytest.mark.asyncio
async def test_process_job_skipped_by_compliance(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
        audit_record=record_audit,
    )

    service._followup_repo_factory = lambda c: store

    rule = await store.create_followup_rule(
        tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
    )
    original_msg_id = uuid.uuid4()
    draft_id = uuid.uuid4()

    schedule = await store.create_followup_schedule(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        original_outbound_message_id=original_msg_id,
        original_draft_id=draft_id,
        followup_rule_id=rule.id,
        status="queued",
        run_after=_NOW + timedelta(seconds=86400),
        actor_user_id=_ACTOR,
        actor_role="owner",
    )

    import app.repositories.billing_repo
    import app.repositories.compliance_repo
    import app.repositories.draft_repo
    import app.repositories.review_repo
    import app.repositories.safety_repo
    import app.repositories.sending_repo

    fake_draft_repo = _FakeDraftStore()
    fake_sending_repo = _FakeSendingStore()
    fake_review_repo = _FakeReviewStore()
    fake_safety_repo = _FakeSafetyStore()
    fake_billing_repo = _FakeBillingStore(allowed=True)
    fake_compliance_repo = _FakeCompliance(
        suppressed_identifiers={"c@test.com"}
    )  # Suppressed contact

    fake_draft_repo.drafts[draft_id] = _FakeDraft(
        id=draft_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
    )
    fake_sending_repo.messages[original_msg_id] = _FakeOutboundMessage(
        id=original_msg_id,
        tenant_id=_TENANT,
        draft_id=draft_id,
        status="mock_sent",
        sent_at=_NOW,
    )
    fake_review_repo.reviews[uuid.uuid4()] = _FakeReviewItem(
        tenant_id=_TENANT,
        draft_id=draft_id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
    )
    fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="prompt_injection",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="source_trust",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="groundedness",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )

    monkeypatch.setattr(app.repositories.draft_repo, "DraftRepository", lambda c: fake_draft_repo)
    monkeypatch.setattr(
        app.repositories.sending_repo, "SendingRepository", lambda c: fake_sending_repo
    )
    monkeypatch.setattr(
        app.repositories.review_repo, "ReviewRepository", lambda c: fake_review_repo
    )
    monkeypatch.setattr(
        app.repositories.safety_repo, "SafetyRepository", lambda c: fake_safety_repo
    )
    monkeypatch.setattr(
        app.repositories.billing_repo, "BillingRepository", lambda c: fake_billing_repo
    )
    monkeypatch.setattr(
        app.repositories.compliance_repo, "ComplianceRepository", lambda c: fake_compliance_repo
    )

    class DummyContact:
        def __init__(self) -> None:
            self.id = _CONTACT
            self.tenant_id = _TENANT
            self.email = "c@test.com"

    class DummyConn:
        async def execute(self, *args: Any, **kwargs: Any) -> Any:
            class DummyResult:
                def scalars(self) -> Any:
                    class DummyScalars:
                        def first(self) -> Any:
                            return DummyContact()

                    return DummyScalars()

            return DummyResult()

    job = JobRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        job_type="send_followup",
        payload={"followup_schedule_id": str(schedule.id)},
        status=JobStatus.QUEUED,
        attempts=0,
        max_attempts=3,
        run_after=_NOW + timedelta(seconds=86400),
        locked_until=None,
        idempotency_key="key_2",
        last_error=None,
    )

    # Act
    await service.process_job(job, DummyConn())

    # Assert: schedule updated to skipped
    assert store.schedules[schedule.id].status == "skipped"

    # Assert: audit event followup.skipped emitted
    skipped_audits = [a for a in audits if a["event_type"] == "followup.skipped"]
    assert len(skipped_audits) == 1
    assert skipped_audits[0]["details"]["reason"] == "COMPLIANCE_SUPPRESSED"


# 6. Cancel Scheduled FollowUp
@pytest.mark.asyncio
async def test_cancel_followup() -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    audits = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
        audit_record=record_audit,
    )

    rule = await store.create_followup_rule(
        tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
    )
    schedule = await store.create_followup_schedule(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        original_outbound_message_id=uuid.uuid4(),
        original_draft_id=uuid.uuid4(),
        followup_rule_id=rule.id,
        status="scheduled",
        run_after=_NOW + timedelta(seconds=86400),
        actor_user_id=_ACTOR,
        actor_role="owner",
    )

    # Cancel schedule
    cancelled = await service.cancel_followup(_principal("owner"), schedule_id=schedule.id)
    assert cancelled.status == "canceled"

    # Verify audit event logged
    cancel_audits = [a for a in audits if a["event_type"] == "followup.canceled"]
    assert len(cancel_audits) == 1

    # Cannot cancel completed schedule
    with pytest.raises(AppError) as exc:
        await service.cancel_followup(_principal("owner"), schedule_id=schedule.id)
    assert exc.value.code == "INVALID_STATE"


# 7. Additional gate validation checks for follow-up job processing
@pytest.mark.asyncio
async def test_process_job_skipped_due_to_various_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.repositories.billing_repo
    import app.repositories.compliance_repo
    import app.repositories.draft_repo
    import app.repositories.review_repo
    import app.repositories.safety_repo
    import app.repositories.sending_repo

    class DummyContact:
        def __init__(self) -> None:
            self.id = _CONTACT
            self.tenant_id = _TENANT
            self.email = "c@test.com"

    class DummyConn:
        async def execute(self, *args: Any, **kwargs: Any) -> Any:
            class DummyResult:
                def scalars(self) -> Any:
                    class DummyScalars:
                        def first(self) -> Any:
                            return DummyContact()

                    return DummyScalars()

            return DummyResult()

    def make_repo_factory(s: Any) -> Callable[[Any], Any]:
        def repo_factory(c: Any) -> Any:
            return s

        return repo_factory

    def make_record_audit(audits_list: list[dict[str, Any]]) -> Callable[..., Any]:
        async def record_audit(audits_list=audits_list, **kwargs: Any) -> None:
            audits_list.append(kwargs)

        return record_audit

    scenarios = [
        ("original_not_sent", True, True, True, True),
        ("billing_denied", False, True, True, True),
        ("safety_failed", True, False, True, True),
        ("safety_missing", True, True, False, True),
        ("review_not_approved", True, True, True, False),
    ]

    for scenario, has_msg, billing_allowed, has_safety, review_approved in scenarios:
        store = _FakeFollowUpStore()
        campaign_store = _FakeCampaignStore()
        draft_store = _FakeDraftStore()
        queue = QueueService(
            _FakeQueueRepo(),
            claim_context=_dummy_claim_context,
            tenant_context=_dummy_tenant_context,
        )
        rbac = RBACService()
        obj_authz = ObjectAuthorizationService()
        billing = BillingGateService(_FakeBillingStore(allowed=billing_allowed))
        audits: list[dict[str, Any]] = []
        record_audit = make_record_audit(audits)

        service = FollowUpSchedulerService(
            followup_store=store,
            campaign_store=campaign_store,
            draft_store=draft_store,
            queue_service=queue,
            rbac=rbac,
            object_authz=obj_authz,
            billing=billing,
            audit_record=record_audit,
        )
        service._followup_repo_factory = make_repo_factory(store)

        rule = await store.create_followup_rule(
            tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
        )
        original_msg_id = uuid.uuid4()
        draft_id = uuid.uuid4()

        schedule = await store.create_followup_schedule(
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            original_outbound_message_id=original_msg_id,
            original_draft_id=draft_id,
            followup_rule_id=rule.id,
            status="queued",
            run_after=_NOW + timedelta(seconds=86400),
            actor_user_id=_ACTOR,
            actor_role="owner",
        )

        fake_draft_repo = _FakeDraftStore()
        fake_sending_repo = _FakeSendingStore()
        fake_review_repo = _FakeReviewStore()
        fake_safety_repo = _FakeSafetyStore()
        fake_billing_repo = _FakeBillingStore(allowed=billing_allowed)
        fake_compliance_repo = _FakeCompliance()

        fake_draft_repo.drafts[draft_id] = _FakeDraft(
            id=draft_id,
            tenant_id=_TENANT,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            status="generated",
        )

        if has_msg and scenario != "original_not_sent":
            fake_sending_repo.messages[original_msg_id] = _FakeOutboundMessage(
                id=original_msg_id,
                tenant_id=_TENANT,
                draft_id=draft_id,
                status="mock_sent",
                sent_at=_NOW,
            )

        fake_review_repo.reviews[uuid.uuid4()] = _FakeReviewItem(
            tenant_id=_TENANT,
            draft_id=draft_id,
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            status="approved" if review_approved else "pending_review",
        )

        if has_safety:
            status = "passed" if scenario != "safety_failed" else "failed"
            fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
                id=uuid.uuid4(),
                tenant_id=_TENANT,
                campaign_id=_CAMPAIGN,
                contact_id=_CONTACT,
                draft_id=draft_id,
                gate_type="prompt_injection",
                status=status,
                severity="low",
                reason_code="passed",
                safe_details={},
                created_at=_NOW,
            )
            fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
                id=uuid.uuid4(),
                tenant_id=_TENANT,
                campaign_id=_CAMPAIGN,
                contact_id=_CONTACT,
                draft_id=draft_id,
                gate_type="source_trust",
                status=status,
                severity="low",
                reason_code="passed",
                safe_details={},
                created_at=_NOW,
            )
            fake_safety_repo.results[uuid.uuid4()] = SafetyGateResultRecord(
                id=uuid.uuid4(),
                tenant_id=_TENANT,
                campaign_id=_CAMPAIGN,
                contact_id=_CONTACT,
                draft_id=draft_id,
                gate_type="groundedness",
                status=status,
                severity="low",
                reason_code="passed",
                safe_details={},
                created_at=_NOW,
            )

        monkeypatch.setattr(
            app.repositories.draft_repo,
            "DraftRepository",
            lambda c, r=fake_draft_repo: r,
        )
        monkeypatch.setattr(
            app.repositories.sending_repo,
            "SendingRepository",
            lambda c, r=fake_sending_repo: r,
        )
        monkeypatch.setattr(
            app.repositories.review_repo,
            "ReviewRepository",
            lambda c, r=fake_review_repo: r,
        )
        monkeypatch.setattr(
            app.repositories.safety_repo,
            "SafetyRepository",
            lambda c, r=fake_safety_repo: r,
        )
        monkeypatch.setattr(
            app.repositories.billing_repo,
            "BillingRepository",
            lambda c, r=fake_billing_repo: r,
        )
        monkeypatch.setattr(
            app.repositories.compliance_repo,
            "ComplianceRepository",
            lambda c, r=fake_compliance_repo: r,
        )

        job = JobRecord(
            id=uuid.uuid4(),
            tenant_id=_TENANT,
            job_type="send_followup",
            payload={"followup_schedule_id": str(schedule.id)},
            status=JobStatus.QUEUED,
            attempts=0,
            max_attempts=3,
            run_after=_NOW + timedelta(seconds=86400),
            locked_until=None,
            idempotency_key=f"key_{scenario}",
            last_error=None,
        )

        # Act
        await service.process_job(job, DummyConn())

        # Assert: schedule updated to skipped
        assert store.schedules[schedule.id].status == "skipped"
        skipped_audits = [a for a in audits if a["event_type"] == "followup.skipped"]
        assert len(skipped_audits) == 1


# 8. Test duplicate scheduling denied
@pytest.mark.asyncio
async def test_schedule_followup_duplicate_denied() -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
    )

    await store.create_followup_rule(tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400)
    draft_id = uuid.uuid4()
    msg_id = uuid.uuid4()

    draft_store.drafts[draft_id] = _FakeDraft(
        id=draft_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
    )

    await service.schedule_followup(
        _principal("owner"),
        draft_id=draft_id,
        outbound_message_id=msg_id,
        now=_NOW,
    )

    with pytest.raises(AppError) as exc:
        await service.schedule_followup(
            _principal("owner"),
            draft_id=draft_id,
            outbound_message_id=msg_id,
            now=_NOW,
        )
    assert exc.value.code == "DUPLICATE_FOLLOWUP"


# 9. Test duplicate followup send (idempotency) and schedule not queued denies/skips
@pytest.mark.asyncio
async def test_process_job_duplicate_or_not_queued() -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
    )
    service._followup_repo_factory = lambda c: store

    rule = await store.create_followup_rule(
        tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
    )
    original_msg_id = uuid.uuid4()
    draft_id = uuid.uuid4()

    schedule = await store.create_followup_schedule(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        original_outbound_message_id=original_msg_id,
        original_draft_id=draft_id,
        followup_rule_id=rule.id,
        status="mock_sent",
        run_after=_NOW + timedelta(seconds=86400),
        actor_user_id=_ACTOR,
        actor_role="owner",
    )

    job = JobRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        job_type="send_followup",
        payload={"followup_schedule_id": str(schedule.id)},
        status=JobStatus.QUEUED,
        attempts=0,
        max_attempts=3,
        run_after=_NOW + timedelta(seconds=86400),
        locked_until=None,
        idempotency_key="key_dup",
        last_error=None,
    )

    await service.process_job(job, object())
    assert store.schedules[schedule.id].status == "mock_sent"


# 10. Test that normal duplicate check still blocks duplicate draft sending when is_followup=False
@pytest.mark.asyncio
async def test_send_gate_normal_duplicate_still_denied() -> None:
    sending_store = _FakeSendingStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    safety_store = _FakeSafetyStore()
    contact_store = _FakeContactStore()
    compliance = _FakeCompliance()
    billing = BillingGateService(_FakeBillingStore(allowed=True))

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

    draft_id = uuid.uuid4()
    draft_store.drafts[draft_id] = _FakeDraft(
        id=draft_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
    )
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="c@test.com"
    )

    review_store.reviews[uuid.uuid4()] = _FakeReviewItem(
        tenant_id=_TENANT,
        draft_id=draft_id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="approved",
    )

    safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="prompt_injection",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="source_trust",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )
    safety_store.results[uuid.uuid4()] = SafetyGateResultRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
        gate_type="groundedness",
        status="passed",
        severity="low",
        reason_code="passed",
        safe_details={},
        created_at=_NOW,
    )

    await sending_store.create_outbound_message(
        tenant_id=_TENANT,
        draft_id=draft_id,
        status="mock_sent",
    )

    with pytest.raises(AppError) as exc:
        await send_gate.evaluate_gate(
            principal=_principal("owner"),
            draft_id=draft_id,
            now=_NOW,
            is_followup=False,
        )
    assert exc.value.code == "DUPLICATE_SEND"


# 11. Test cross-tenant follow-up operations are denied
@pytest.mark.asyncio
async def test_cross_tenant_followup_denied() -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
    )

    # A campaign owned by OTHER_TENANT
    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_OTHER_TENANT)

    # 11.a Rule creation denied for tenant mismatch
    with pytest.raises(AppError) as exc:
        await service.create_followup_rule(
            _principal("owner", tenant_id=_TENANT),
            campaign_id=_CAMPAIGN,
            delay_seconds=86400,
        )
    assert exc.value.code == "CAMPAIGN_NOT_FOUND"

    # A draft owned by OTHER_TENANT
    draft_id = uuid.uuid4()
    draft_store.drafts[draft_id] = _FakeDraft(
        id=draft_id,
        tenant_id=_OTHER_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
    )

    # 11.b Scheduling denied for tenant mismatch
    with pytest.raises(AppError) as exc:
        await service.schedule_followup(
            _principal("owner", tenant_id=_TENANT),
            draft_id=draft_id,
            outbound_message_id=uuid.uuid4(),
            now=_NOW,
        )
    assert exc.value.code == "DRAFT_NOT_FOUND"

    # A rule and schedule for OTHER_TENANT
    rule = await store.create_followup_rule(
        tenant_id=_OTHER_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
    )
    schedule = await store.create_followup_schedule(
        tenant_id=_OTHER_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        original_outbound_message_id=uuid.uuid4(),
        original_draft_id=draft_id,
        followup_rule_id=rule.id,
        status="scheduled",
        run_after=_NOW + timedelta(seconds=86400),
        actor_user_id=_ACTOR,
        actor_role="owner",
    )

    # 11.c Cancellation denied for tenant mismatch
    with pytest.raises(AppError) as exc:
        await service.cancel_followup(
            _principal("owner", tenant_id=_TENANT),
            schedule_id=schedule.id,
        )
    assert exc.value.code == "FOLLOWUP_SCHEDULE_NOT_FOUND"

    # 11.d Background processing tenant mismatch check
    # Setup job on TENANT but referencing OTHER_TENANT's schedule
    service._followup_repo_factory = lambda c: store
    job = JobRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        job_type="send_followup",
        payload={"followup_schedule_id": str(schedule.id)},
        status=JobStatus.QUEUED,
        attempts=0,
        max_attempts=3,
        run_after=_NOW + timedelta(seconds=86400),
        locked_until=None,
        idempotency_key="key_tenant_mismatch",
        last_error=None,
    )

    with pytest.raises(AppError) as exc:
        await service.process_job(job, object())
    assert exc.value.code == "FOLLOWUP_SCHEDULE_NOT_FOUND"


# 12. Test that scheduled follow-up job uses tenant context and correct tenant_id
@pytest.mark.asyncio
async def test_queue_job_uses_tenant_context() -> None:
    store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    draft_store = _FakeDraftStore()
    queue = QueueService(
        _FakeQueueRepo(), claim_context=_dummy_claim_context, tenant_context=_dummy_tenant_context
    )
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    billing = BillingGateService(_FakeBillingStore(allowed=True))

    service = FollowUpSchedulerService(
        followup_store=store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
    )

    await store.create_followup_rule(tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400)
    draft_id = uuid.uuid4()
    draft_store.drafts[draft_id] = _FakeDraft(
        id=draft_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
    )

    # Schedule follow-up
    await service.schedule_followup(
        _principal("owner", tenant_id=_TENANT),
        draft_id=draft_id,
        outbound_message_id=uuid.uuid4(),
        now=_NOW,
    )

    # Verify that the enqueued job has the correct tenant_id
    assert isinstance(queue._repo, _FakeQueueRepo)
    jobs = list(queue._repo.jobs.values())
    assert len(jobs) == 1
    assert jobs[0].tenant_id == _TENANT
    assert jobs[0].job_type == "send_followup"
