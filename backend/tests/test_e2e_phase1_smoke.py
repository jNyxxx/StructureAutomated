"""Phase 1 E2E smoke test (P1-13).

Single happy-path test exercising all 23 steps of the local/mock MVP backend
flow using real service classes with in-memory fake stores. No live DB, no real
providers, no secrets.

Negative checks verify gate enforcement on every major guard point.
"""

from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

import app.repositories.billing_repo
import app.repositories.compliance_repo
import app.repositories.draft_repo
import app.repositories.review_repo
import app.repositories.safety_repo
import app.repositories.sending_repo
from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.models.job import JobStatus
from app.repositories.deliverability_repo import (
    DeliverabilityTrendPoint,
    FollowupCounts,
    GateCounts,
    OutboundCounts,
)
from app.repositories.followup_repo import FollowUpRuleRecord, FollowUpScheduleRecord
from app.repositories.outcomes_repo import (
    OutcomeEventRecord,
    OutcomeTrendPoint,
    OutcomeTypeCounts,
    ROIAssumptionsRecord,
)
from app.repositories.review_repo import ReviewRecord
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import (
    BillingAccessDenied,
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)
from app.services.deliverability import DeliverabilityService
from app.services.followup_scheduler import FollowUpSchedulerService
from app.services.groundedness import GroundednessService
from app.services.mock_sender import MockSenderService
from app.services.outcomes import (
    FunnelSummary,
    OutcomesService,
    ROISummary,
)
from app.services.queue import JobRecord, QueueService
from app.services.rag_grounding import GroundingChunk
from app.services.review import ReviewService
from app.services.safety import SafetyGateResultRecord, SafetyService
from app.services.send_gate import SendGateService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_PLAN_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_NOW = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)


def _principal(
    role: str = "owner",
    *,
    tenant_id: uuid.UUID = _TENANT,
) -> CurrentPrincipal:
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


# ---------------------------------------------------------------------------
# Fake stores
# ---------------------------------------------------------------------------


class _FakeBillingStore:
    def __init__(self, *, allowed: bool = True) -> None:
        self.record = TenantSubscriptionRecord(
            tenant_id=_TENANT,
            tenant_status="active" if allowed else "inactive",
            plan=BillingPlan(
                id=_PLAN_ID,
                key="mvp_mock",
                name="MVP Mock Plan",
                features={
                    "can_send": allowed,
                    "can_run_agents": allowed,
                    "can_create_campaign": allowed,
                    "can_import_contacts": allowed,
                },
            ),
        )

    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        return self.record if tenant_id == self.record.tenant_id else None

    async def set_status(self, **kwargs: Any) -> Any:
        raise AssertionError("not used in smoke test")


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
        self,
        *,
        tenant_id: uuid.UUID,
        result_id: uuid.UUID,
        draft_id: uuid.UUID,
    ) -> SafetyGateResultRecord | None:
        rec = self.results.get(result_id)
        if rec is not None and rec.tenant_id == tenant_id:
            updated = replace(rec, draft_id=draft_id)
            self.results[result_id] = updated
            return updated
        return None

    async def list_results_for_context(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> list[SafetyGateResultRecord]:
        out = []
        for r in self.results.values():
            if r.tenant_id != tenant_id:
                continue
            if draft_id is not None and r.draft_id != draft_id:
                continue
            out.append(r)
        return out


@dataclass(frozen=True)
class _FakeDraftRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str
    subject: str
    body: str
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime


class _FakeDraftStore:
    def __init__(self) -> None:
        self.drafts: dict[uuid.UUID, _FakeDraftRecord] = {}

    async def get_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> _FakeDraftRecord | None:
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
    ) -> _FakeDraftRecord:
        draft = _FakeDraftRecord(
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

    async def update_draft_status(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID, status: str
    ) -> _FakeDraftRecord | None:
        d = self.drafts.get(draft_id)
        if d is not None and d.tenant_id == tenant_id:
            updated = replace(d, status=status, updated_at=_NOW)
            self.drafts[draft_id] = updated
            return updated
        return None


class _FakeReviewStore:
    def __init__(self) -> None:
        self.reviews: dict[uuid.UUID, ReviewRecord] = {}

    def add(self, rec: ReviewRecord) -> None:
        self.reviews[rec.id] = rec

    async def create_review_item(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str = "pending_review",
    ) -> ReviewRecord:
        rec = ReviewRecord(
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
        self.reviews[rec.id] = rec
        return rec

    async def get_review_item(
        self, *, tenant_id: uuid.UUID, review_id: uuid.UUID
    ) -> ReviewRecord | None:
        r = self.reviews.get(review_id)
        if r is not None and r.tenant_id == tenant_id:
            return r
        return None

    async def get_review_item_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> ReviewRecord | None:
        for r in self.reviews.values():
            if r.draft_id == draft_id and r.tenant_id == tenant_id:
                return r
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
        r = self.reviews.get(review_id)
        if r is not None and r.tenant_id == tenant_id:
            updated = replace(
                r,
                status=status,
                reviewer_user_id=reviewer_user_id,
                action_reason=action_reason,
                reviewed_at=reviewed_at,
                updated_at=_NOW,
            )
            self.reviews[review_id] = updated
            return updated
        return None

    async def list_review_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[ReviewRecord]:
        out = []
        for r in self.reviews.values():
            if r.tenant_id != tenant_id:
                continue
            if campaign_id is not None and r.campaign_id != campaign_id:
                continue
            if status is not None and r.status != status:
                continue
            out.append(r)
        return out


@dataclass(frozen=True)
class _FakeContact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str = "prospect@example.com"


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


class _FakeKnowledgeStore:
    """Minimal stub — only used when knowledge_chunk type sources are checked."""

    async def get_chunk(self, *, tenant_id: uuid.UUID, chunk_id: uuid.UUID) -> None:
        return None

    async def get_document(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        return None


@dataclass(frozen=True)
class _FakeArtifact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    findings: dict[str, Any]


class _FakeResearchStore:
    def __init__(self) -> None:
        self.artifacts: dict[uuid.UUID, _FakeArtifact] = {}

    async def get_artifact(
        self, *, tenant_id: uuid.UUID, artifact_id: uuid.UUID
    ) -> _FakeArtifact | None:
        a = self.artifacts.get(artifact_id)
        if a is not None and a.tenant_id == tenant_id:
            return a
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

    async def create_gate_result(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        deny_reason_code: str | None = None,
    ) -> dict[str, Any]:
        res: dict[str, Any] = {
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
        if job_id in self.jobs:
            self.jobs[job_id] = replace(self.jobs[job_id], **fields)


class _FakeComplianceGate:
    def __init__(self, suppressed: set[str] | None = None) -> None:
        self._suppressed = suppressed or set()

    async def is_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> bool:
        return contact_identifier in self._suppressed

    async def get_active_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
    ) -> Any | None:
        from app.services.compliance import hash_contact_identifier

        for identifier in self._suppressed:
            h = hash_contact_identifier(channel=channel, contact_identifier=identifier)
            if h == contact_hash:
                return object()
        return None


class _FakeDeliverabilityStore:
    def __init__(self) -> None:
        self._outbound: dict[tuple[uuid.UUID, uuid.UUID | None], OutboundCounts] = {}
        self._gates: dict[tuple[uuid.UUID, uuid.UUID | None], GateCounts] = {}
        self._followups: dict[tuple[uuid.UUID, uuid.UUID | None], FollowupCounts] = {}
        self._trend: list[DeliverabilityTrendPoint] = []

    def set_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        outbound: OutboundCounts | None = None,
        gates: GateCounts | None = None,
        followups: FollowupCounts | None = None,
    ) -> None:
        if outbound:
            self._outbound[(tenant_id, None)] = outbound
        if gates:
            self._gates[(tenant_id, None)] = gates
        if followups:
            self._followups[(tenant_id, None)] = followups

    async def get_outbound_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> OutboundCounts:
        return self._outbound.get((tenant_id, campaign_id), OutboundCounts(sent=0, blocked=0))

    async def get_gate_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> GateCounts:
        return self._gates.get(
            (tenant_id, campaign_id),
            GateCounts(duplicate_denied=0, suppressed=0, safety_denied=0, throttled=0),
        )

    async def get_followup_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> FollowupCounts:
        return self._followups.get(
            (tenant_id, campaign_id),
            FollowupCounts(followup_sent=0, followup_skipped=0),
        )

    async def get_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> list[DeliverabilityTrendPoint]:
        return list(self._trend)


@dataclass
class _FakeOutcomeTypeCounts:
    reply_received: int = 0
    positive_reply: int = 0
    meeting_booked: int = 0
    opportunity_created: int = 0
    deal_won: int = 0
    deal_lost: int = 0
    unsubscribed: int = 0
    bounced: int = 0
    complaint: int = 0


class _FakeOutcomesStore:
    def __init__(self) -> None:
        self.events: dict[uuid.UUID, OutcomeEventRecord] = {}
        self.idem_index: dict[str, uuid.UUID] = {}
        self.assumptions: dict[uuid.UUID, ROIAssumptionsRecord] = {}
        self._counts: dict[tuple[uuid.UUID, uuid.UUID | None], _FakeOutcomeTypeCounts] = {}
        self._trend: list[OutcomeTrendPoint] = []

    def set_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        counts: _FakeOutcomeTypeCounts,
    ) -> None:
        self._counts[(tenant_id, campaign_id)] = counts

    async def create_outcome_event(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        event_type: str,
        outbound_message_id: uuid.UUID | None,
        note: str | None,
        idempotency_key: str | None,
        occurred_at: datetime | None,
    ) -> OutcomeEventRecord:
        if idempotency_key is not None and idempotency_key in self.idem_index:
            return self.events[self.idem_index[idempotency_key]]
        eid = uuid.uuid4()
        rec = OutcomeEventRecord(
            id=eid,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            outbound_message_id=outbound_message_id,
            event_type=event_type,
            note=note,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at or _NOW,
            created_at=_NOW,
        )
        self.events[eid] = rec
        if idempotency_key is not None:
            self.idem_index[idempotency_key] = eid
        return rec

    async def get_outcome_event(
        self, *, tenant_id: uuid.UUID, event_id: uuid.UUID
    ) -> OutcomeEventRecord | None:
        ev = self.events.get(event_id)
        if ev is not None and ev.tenant_id == tenant_id:
            return ev
        return None

    async def get_outcome_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> OutcomeTypeCounts:
        raw = self._counts.get((tenant_id, campaign_id), _FakeOutcomeTypeCounts())
        return OutcomeTypeCounts(
            reply_received=raw.reply_received,
            positive_reply=raw.positive_reply,
            meeting_booked=raw.meeting_booked,
            opportunity_created=raw.opportunity_created,
            deal_won=raw.deal_won,
            deal_lost=raw.deal_lost,
            unsubscribed=raw.unsubscribed,
            bounced=raw.bounced,
            complaint=raw.complaint,
        )

    async def upsert_roi_assumptions(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        cost_per_send_cents: int,
        pipeline_value_per_opportunity_cents: int,
        revenue_per_deal_won_cents: int,
    ) -> ROIAssumptionsRecord:
        rec = ROIAssumptionsRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            cost_per_send_cents=cost_per_send_cents,
            pipeline_value_per_opportunity_cents=pipeline_value_per_opportunity_cents,
            revenue_per_deal_won_cents=revenue_per_deal_won_cents,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.assumptions[campaign_id] = rec
        return rec

    async def get_roi_assumptions(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> ROIAssumptionsRecord | None:
        return self.assumptions.get(campaign_id)

    async def get_outcome_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[OutcomeTrendPoint]:
        return list(self._trend)


class _FakeSendCountStore:
    def __init__(self, count: int = 0) -> None:
        self._count = count

    async def get_sent_count(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        return self._count


# ---------------------------------------------------------------------------
# Queue context managers (dummy)
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def _dummy_claim_ctx() -> Any:
    yield object()


@contextlib.asynccontextmanager
async def _dummy_tenant_ctx(tenant_id: uuid.UUID) -> Any:
    yield object()


# ---------------------------------------------------------------------------
# Happy path E2E test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_e2e_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise all 23 P1 flow steps with real services + in-memory stores."""

    # -----------------------------------------------------------------------
    # Shared stores (all services reference the same instances)
    # -----------------------------------------------------------------------
    billing_store = _FakeBillingStore(allowed=True)
    billing = BillingGateService(billing_store)
    rbac = RBACService()
    obj_authz = ObjectAuthorizationService()
    audits: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audits.append(kwargs)

    safety_store = _FakeSafetyStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    contact_store = _FakeContactStore()
    knowledge_store = _FakeKnowledgeStore()
    research_store = _FakeResearchStore()
    sending_store = _FakeSendingStore()
    followup_store = _FakeFollowUpStore()
    campaign_store = _FakeCampaignStore()
    queue_repo = _FakeQueueRepo()
    compliance = _FakeComplianceGate()
    deliverability_store = _FakeDeliverabilityStore()
    outcomes_store = _FakeOutcomesStore()
    send_count_store = _FakeSendCountStore(count=1)

    queue_svc = QueueService(
        queue_repo,
        claim_context=_dummy_claim_ctx,
        tenant_context=_dummy_tenant_ctx,
    )

    safety_svc = SafetyService(
        safety_store=safety_store,
        knowledge_store=knowledge_store,  # type: ignore[arg-type]
        audit_record=record_audit,
    )

    groundedness_svc = GroundednessService(
        safety_store=safety_store,
        knowledge_store=knowledge_store,  # type: ignore[arg-type]
        research_store=research_store,
        audit_record=record_audit,
    )

    review_svc = ReviewService(
        review_store=review_store,
        draft_store=draft_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=rbac,
        compliance=compliance,
        audit_record=record_audit,
    )

    send_gate_svc = SendGateService(
        sending_store=sending_store,
        draft_store=draft_store,
        review_store=review_store,
        safety_store=safety_store,
        contact_store=contact_store,
        billing=billing,
        rbac=rbac,
        object_authz=obj_authz,
        compliance=compliance,
        audit_record=record_audit,
    )

    followup_svc = FollowUpSchedulerService(
        followup_store=followup_store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue_svc,
        rbac=rbac,
        object_authz=obj_authz,
        billing=billing,
        audit_record=record_audit,
    )

    sender_svc = MockSenderService(
        sending_store=sending_store,
        send_gate=send_gate_svc,
        followups=followup_svc,
        audit_record=record_audit,
    )

    deliverability_svc = DeliverabilityService(
        store=deliverability_store,
        rbac=rbac,
        object_authz=obj_authz,
    )

    outcomes_svc = OutcomesService(
        store=outcomes_store,
        send_count_store=send_count_store,
        rbac=rbac,
        object_authz=obj_authz,
    )

    principal = _principal()

    # -----------------------------------------------------------------------
    # Step 1: Principal and tenant context established
    # -----------------------------------------------------------------------
    assert principal.tenant_id == _TENANT
    assert principal.role == "owner"

    # -----------------------------------------------------------------------
    # Steps 2-4: CSV import → campaign → contact selection (simulated)
    # These steps are fully covered by individual test suites.
    # Here we inject the resulting state directly.
    # -----------------------------------------------------------------------
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="prospect@example.com"
    )
    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)

    # -----------------------------------------------------------------------
    # Steps 5-6: Research run + artifacts (simulated)
    # -----------------------------------------------------------------------
    artifact_id = uuid.uuid4()
    research_store.artifacts[artifact_id] = _FakeArtifact(
        id=artifact_id,
        tenant_id=_TENANT,
        findings={"company": "Acme Corp", "role": "CTO", "priority_pain": "scaling infra"},
    )

    # -----------------------------------------------------------------------
    # Steps 7-8: Knowledge document + chunks (simulated)
    # Using research_artifact type chunks avoids knowledge_store get_chunk calls.
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # Step 9: RAG grounding context — build GroundingChunk list
    # -----------------------------------------------------------------------
    chunks = [
        GroundingChunk(
            source_type="research_artifact",
            source_id=artifact_id,
            content="Acme Corp CTO is focused on scaling infrastructure for 10× growth.",
            tenant_id=_TENANT,
            score=0.95,
        )
    ]

    # -----------------------------------------------------------------------
    # Step 10: Draft generation (simulated — DraftGenerationService covered
    # by its own test suite; we inject the resulting draft record here)
    # -----------------------------------------------------------------------
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Scaling infrastructure at Acme Corp",
        body="Hi, I noticed Acme is investing in scaling its infrastructure.",
    )
    draft_id = draft.id

    # -----------------------------------------------------------------------
    # Step 11: Prompt-injection + source-trust safety gates (REAL service)
    # -----------------------------------------------------------------------
    safety_results = await safety_svc.evaluate_grounding_safety(
        principal=principal,
        chunks=chunks,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
    )
    assert len(safety_results) == 2
    gate_types = {r.gate_type for r in safety_results}
    assert "prompt_injection" in gate_types
    assert "source_trust" in gate_types
    for r in safety_results:
        assert r.status == "passed"
        assert r.tenant_id == _TENANT
        assert r.draft_id == draft_id

    # -----------------------------------------------------------------------
    # Step 12: Groundedness / citation validation (REAL service)
    # -----------------------------------------------------------------------
    groundedness_result = await groundedness_svc.evaluate_draft_groundedness(
        principal=principal,
        subject=draft.subject,
        body=draft.body,
        chunks=chunks,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        draft_id=draft_id,
    )
    assert groundedness_result.gate_type == "groundedness"
    assert groundedness_result.status == "passed"
    assert groundedness_result.tenant_id == _TENANT
    assert groundedness_result.draft_id == draft_id

    # Verify all 3 safety results are now in the store for this draft
    all_safety = await safety_store.list_results_for_context(tenant_id=_TENANT, draft_id=draft_id)
    assert {r.gate_type for r in all_safety} == {
        "prompt_injection",
        "source_trust",
        "groundedness",
    }

    # -----------------------------------------------------------------------
    # Step 13: Human review item created (simulated — DraftGenerationService
    # creates review items as part of draft creation)
    # -----------------------------------------------------------------------
    review_item = ReviewRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        draft_id=draft_id,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="pending_review",
        reviewer_user_id=None,
        action_reason=None,
        reviewed_at=None,
        created_at=_NOW,
        updated_at=_NOW,
    )
    review_store.add(review_item)
    review_id = review_item.id

    # Verify queue has the pending item
    queue_items = await review_svc.list_review_queue(principal, status="pending_review")
    assert len(queue_items) == 1
    assert queue_items[0].draft_id == draft_id

    # -----------------------------------------------------------------------
    # Step 14: Approve valid draft (REAL service)
    # -----------------------------------------------------------------------
    approved_item = await review_svc.approve_draft(
        principal,
        review_id=review_id,
        now=_NOW,
    )
    assert approved_item is not None
    assert approved_item.status == "approved"

    # Confirm audit event was recorded
    approve_audits = [a for a in audits if a["event_type"] == "draft.approved"]
    assert len(approve_audits) == 1

    # -----------------------------------------------------------------------
    # Step 15-16: Run send gate + mock send approved draft (REAL service)
    # Requires follow-up rule to exist so auto-scheduling fires.
    # -----------------------------------------------------------------------
    await followup_store.create_followup_rule(
        tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=86400
    )

    send_result = await sender_svc.send_approved_draft(
        principal,
        draft_id=draft_id,
        now=_NOW,
    )
    assert send_result.status == "mock_sent"
    assert send_result.outbound_message_id is not None

    sent_audits = [a for a in audits if a["event_type"] == "outbound_message.sent"]
    assert len(sent_audits) == 1
    gate_passed_audits = [a for a in audits if a["event_type"] == "send_gate.passed"]
    assert len(gate_passed_audits) == 1

    # Verify outbound message recorded in sending store
    sent_msg = await sending_store.get_outbound_message_by_draft(
        tenant_id=_TENANT, draft_id=draft_id
    )
    assert sent_msg is not None
    assert sent_msg.status == "mock_sent"

    # -----------------------------------------------------------------------
    # Step 17: Duplicate send prevention — same draft must be blocked
    # -----------------------------------------------------------------------
    with pytest.raises(AppError) as exc_info:
        await sender_svc.send_approved_draft(principal, draft_id=draft_id, now=_NOW)
    assert exc_info.value.code == "DUPLICATE_SEND"

    # -----------------------------------------------------------------------
    # Step 18: Follow-up scheduled automatically by step 16
    # -----------------------------------------------------------------------
    schedule = await followup_store.get_followup_schedule_by_original_message(
        tenant_id=_TENANT,
        original_outbound_message_id=send_result.outbound_message_id,
    )
    assert schedule is not None
    assert schedule.status == "queued"
    assert schedule.run_after == _NOW + timedelta(seconds=86400)
    assert schedule.original_draft_id == draft_id

    queued_jobs = list(queue_repo.jobs.values())
    assert len(queued_jobs) == 1
    assert queued_jobs[0].job_type == "send_followup"
    assert queued_jobs[0].payload["followup_schedule_id"] == str(schedule.id)

    followup_audits = [a for a in audits if a["event_type"] == "followup.scheduled"]
    assert len(followup_audits) == 1

    # -----------------------------------------------------------------------
    # Step 19: Process mock follow-up job (REAL service, monkeypatched repos)
    # -----------------------------------------------------------------------
    followup_svc._followup_repo_factory = lambda c: followup_store

    monkeypatch.setattr(app.repositories.draft_repo, "DraftRepository", lambda c: draft_store)
    monkeypatch.setattr(app.repositories.sending_repo, "SendingRepository", lambda c: sending_store)
    monkeypatch.setattr(app.repositories.review_repo, "ReviewRepository", lambda c: review_store)
    monkeypatch.setattr(app.repositories.safety_repo, "SafetyRepository", lambda c: safety_store)
    monkeypatch.setattr(app.repositories.billing_repo, "BillingRepository", lambda c: billing_store)
    monkeypatch.setattr(
        app.repositories.compliance_repo, "ComplianceRepository", lambda c: compliance
    )

    class _DummyContact:
        def __init__(self) -> None:
            self.id = _CONTACT
            self.tenant_id = _TENANT
            self.email = "prospect@example.com"

    class _DummyConn:
        async def execute(self, *args: Any, **kwargs: Any) -> Any:
            class _DummyResult:
                def scalars(self) -> Any:
                    class _DummyScalars:
                        def first(self) -> Any:
                            return _DummyContact()

                    return _DummyScalars()

            return _DummyResult()

    job_record = JobRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        job_type="send_followup",
        payload={"followup_schedule_id": str(schedule.id)},
        status=JobStatus.QUEUED,
        attempts=0,
        max_attempts=3,
        run_after=schedule.run_after,
        locked_until=None,
        idempotency_key=f"followup-{schedule.id}",
        last_error=None,
    )

    await followup_svc.process_job(job_record, _DummyConn())

    followup_after = await followup_store.get_followup_schedule(
        tenant_id=_TENANT, schedule_id=schedule.id
    )
    assert followup_after is not None
    assert followup_after.status == "mock_sent"

    mock_sent_audits = [a for a in audits if a["event_type"] == "followup.mock_sent"]
    assert len(mock_sent_audits) == 1

    # -----------------------------------------------------------------------
    # Step 20: Aggregate deliverability summary (REAL service, fake counts)
    # -----------------------------------------------------------------------
    deliverability_store.set_counts(
        tenant_id=_TENANT,
        outbound=OutboundCounts(sent=2, blocked=0),
        gates=GateCounts(duplicate_denied=1, suppressed=0, safety_denied=0, throttled=0),
        followups=FollowupCounts(followup_sent=1, followup_skipped=0),
    )

    delivery_summary = await deliverability_svc.get_tenant_summary(principal)
    assert delivery_summary.tenant_id == _TENANT
    assert delivery_summary.sent == 2
    assert delivery_summary.followup_sent == 1
    assert delivery_summary.duplicate_denied == 1
    assert delivery_summary.mock_opened == int(2 * 0.35)

    # -----------------------------------------------------------------------
    # Step 21: Record mock outcome event (REAL service)
    # -----------------------------------------------------------------------
    outcome_event = await outcomes_svc.record_outcome_event(
        principal,
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        contact_id=_CONTACT,
        contact_tenant_id=_TENANT,
        event_type="reply_received",
        outbound_message_id=send_result.outbound_message_id,
        idempotency_key=f"reply-{send_result.outbound_message_id}",
    )
    assert outcome_event.event_type == "reply_received"
    assert outcome_event.tenant_id == _TENANT
    assert outcome_event.campaign_id == _CAMPAIGN

    # Idempotency: second call with same key must return the same event
    outcome_event_2 = await outcomes_svc.record_outcome_event(
        principal,
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        contact_id=_CONTACT,
        contact_tenant_id=_TENANT,
        event_type="reply_received",
        outbound_message_id=send_result.outbound_message_id,
        idempotency_key=f"reply-{send_result.outbound_message_id}",
    )
    assert outcome_event_2.id == outcome_event.id

    # -----------------------------------------------------------------------
    # Step 22: Aggregate outcomes / ROI / funnel summaries (REAL service)
    # -----------------------------------------------------------------------
    await outcomes_svc.set_roi_assumptions(
        principal,
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        cost_per_send_cents=100,
        pipeline_value_per_opportunity_cents=50000,
        revenue_per_deal_won_cents=200000,
    )

    # Inject some outcome counts so funnel math works
    outcomes_store.set_counts(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        counts=_FakeOutcomeTypeCounts(
            reply_received=5,
            meeting_booked=2,
            opportunity_created=1,
            deal_won=1,
        ),
    )

    roi = await outcomes_svc.get_roi_summary(
        principal,
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        sent_count=10,
    )
    assert isinstance(roi, ROISummary)
    assert roi.tenant_id == _TENANT
    assert roi.campaign_id == _CAMPAIGN
    assert roi.sent_count == 10
    assert roi.estimated_cost_cents == 1000
    assert roi.estimated_pipeline_value_cents == 50000
    assert roi.estimated_won_value_cents == 200000
    assert roi.estimated_roi_percent is not None
    assert roi.estimated_roi_percent == round((200000 - 1000) / 1000 * 100, 2)

    funnel = await outcomes_svc.get_funnel_summary(
        principal,
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        sent_count=10,
    )
    assert isinstance(funnel, FunnelSummary)
    assert funnel.sent == 10
    assert funnel.replied == 5
    assert funnel.meeting_booked == 2
    assert funnel.opportunity == 1
    assert funnel.deal_won == 1
    assert funnel.sent_to_reply_rate == round(5 / 10, 4)

    # -----------------------------------------------------------------------
    # Step 23: Verify key audit events were emitted
    # -----------------------------------------------------------------------
    event_types = {a["event_type"] for a in audits}
    assert "draft.approved" in event_types
    assert "send_gate.passed" in event_types
    assert "outbound_message.sent" in event_types
    assert "followup.scheduled" in event_types
    assert "followup.mock_sent" in event_types

    # No secrets in any audit detail value
    for audit in audits:
        for val in audit.get("details", {}).values():
            val_str = str(val).lower()
            for forbidden in ("secret", "password", "api_key", "token", "credential"):
                assert (
                    forbidden not in val_str
                ), f"Sensitive pattern '{forbidden}' leaked in audit details"


# ---------------------------------------------------------------------------
# Negative checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suppressed_contact_blocks_send() -> None:
    """contact_suppressed → send gate raises AppError."""
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    safety_store = _FakeSafetyStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    contact_store = _FakeContactStore()
    sending_store = _FakeSendingStore()

    suppressed_email = "blocked@suppressed.test"
    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email=suppressed_email
    )

    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Test",
        body="Test body",
    )
    for gate in ("prompt_injection", "source_trust", "groundedness"):
        await safety_store.create_result(
            tenant_id=_TENANT,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="passed",
            safe_details={},
            campaign_id=_CAMPAIGN,
            contact_id=_CONTACT,
            draft_id=draft.id,
        )
    review_store.add(
        ReviewRecord(
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
    )

    compliance = _FakeComplianceGate(suppressed={suppressed_email})
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
    sender = MockSenderService(sending_store=sending_store, send_gate=send_gate)

    with pytest.raises(AppError) as exc_info:
        await sender.send_approved_draft(_principal(), draft_id=draft.id, now=_NOW)
    assert exc_info.value.code in ("COMPLIANCE_SUPPRESSED", "SAFETY_GATE_FAILED")


@pytest.mark.asyncio
async def test_missing_safety_blocks_send() -> None:
    """No safety results → safety_missing → send gate raises AppError."""
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    safety_store = _FakeSafetyStore()  # empty
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    contact_store = _FakeContactStore()
    sending_store = _FakeSendingStore()

    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="c@test.com"
    )
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Test",
        body="Body",
    )
    review_store.add(
        ReviewRecord(
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
    )
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
    with pytest.raises(AppError) as exc_info:
        await send_gate.evaluate_gate(_principal(), draft_id=draft.id, now=_NOW)
    assert exc_info.value.code == "SAFETY_GATE_MISSING"


@pytest.mark.asyncio
async def test_failed_safety_blocks_send() -> None:
    """Failed safety result → safety_failed → send gate raises AppError."""
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    safety_store = _FakeSafetyStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    contact_store = _FakeContactStore()
    sending_store = _FakeSendingStore()

    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="c@test.com"
    )
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Test",
        body="Body",
    )
    # Inject a FAILED prompt_injection result
    await safety_store.create_result(
        tenant_id=_TENANT,
        gate_type="prompt_injection",
        status="failed",
        severity="critical",
        reason_code="prompt_injection_detected",
        safe_details={"failed_chunk_ids": ["abc"]},
        draft_id=draft.id,
    )
    review_store.add(
        ReviewRecord(
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
    )
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
    with pytest.raises(AppError) as exc_info:
        await send_gate.evaluate_gate(_principal(), draft_id=draft.id, now=_NOW)
    assert exc_info.value.code == "SAFETY_GATE_FAILED"


@pytest.mark.asyncio
async def test_missing_groundedness_blocks_send() -> None:
    """Missing groundedness result → groundedness_missing → send gate blocks."""
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    safety_store = _FakeSafetyStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    contact_store = _FakeContactStore()
    sending_store = _FakeSendingStore()

    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="c@test.com"
    )
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Test",
        body="Body",
    )
    # Only prompt_injection + source_trust — missing groundedness
    for gate in ("prompt_injection", "source_trust"):
        await safety_store.create_result(
            tenant_id=_TENANT,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="passed",
            safe_details={},
            draft_id=draft.id,
        )
    review_store.add(
        ReviewRecord(
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
    )
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
    with pytest.raises(AppError) as exc_info:
        await send_gate.evaluate_gate(_principal(), draft_id=draft.id, now=_NOW)
    assert exc_info.value.code == "SAFETY_GATE_MISSING"


@pytest.mark.asyncio
async def test_duplicate_send_denied() -> None:
    """Sending same draft twice raises DUPLICATE_SEND on second attempt."""
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    safety_store = _FakeSafetyStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    contact_store = _FakeContactStore()
    sending_store = _FakeSendingStore()

    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="c@test.com"
    )
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Dup",
        body="Dup body",
    )
    for gate in ("prompt_injection", "source_trust", "groundedness"):
        await safety_store.create_result(
            tenant_id=_TENANT,
            gate_type=gate,
            status="passed",
            severity="info",
            reason_code="passed",
            safe_details={},
            draft_id=draft.id,
        )
    review_store.add(
        ReviewRecord(
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
    )
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
    sender = MockSenderService(sending_store=sending_store, send_gate=send_gate)

    await sender.send_approved_draft(_principal(), draft_id=draft.id, now=_NOW)

    with pytest.raises(AppError) as exc_info:
        await sender.send_approved_draft(_principal(), draft_id=draft.id, now=_NOW)
    assert exc_info.value.code == "DUPLICATE_SEND"


@pytest.mark.asyncio
async def test_duplicate_followup_denied() -> None:
    """Scheduling follow-up twice for same message raises DUPLICATE_FOLLOWUP."""
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    followup_store = _FakeFollowUpStore()
    draft_store = _FakeDraftStore()
    campaign_store = _FakeCampaignStore()
    queue_repo = _FakeQueueRepo()
    queue_svc = QueueService(
        queue_repo,
        claim_context=_dummy_claim_ctx,
        tenant_context=_dummy_tenant_ctx,
    )

    campaign_store.campaigns[_CAMPAIGN] = _FakeCampaign(id=_CAMPAIGN, tenant_id=_TENANT)
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="F",
        body="B",
    )
    await followup_store.create_followup_rule(
        tenant_id=_TENANT, campaign_id=_CAMPAIGN, delay_seconds=3600
    )

    svc = FollowUpSchedulerService(
        followup_store=followup_store,
        campaign_store=campaign_store,
        draft_store=draft_store,
        queue_service=queue_svc,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=billing,
    )

    outbound_msg_id = uuid.uuid4()
    await svc.schedule_followup(
        _principal(),
        draft_id=draft.id,
        outbound_message_id=outbound_msg_id,
        now=_NOW,
    )

    with pytest.raises(AppError) as exc_info:
        await svc.schedule_followup(
            _principal(),
            draft_id=draft.id,
            outbound_message_id=outbound_msg_id,
            now=_NOW,
        )
    assert exc_info.value.code == "DUPLICATE_FOLLOWUP"


@pytest.mark.asyncio
async def test_cross_tenant_access_denied() -> None:
    """Principal from another tenant accessing campaign data raises OBJECT_ACCESS_DENIED."""
    svc = DeliverabilityService(
        store=_FakeDeliverabilityStore(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
    )
    with pytest.raises(AppError) as exc_info:
        await svc.get_campaign_summary(
            _principal(tenant_id=_TENANT),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_OTHER_TENANT,
        )
    assert exc_info.value.code == "OBJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_billing_inactive_blocks_send() -> None:
    """Inactive billing subscription blocks the send gate."""
    billing = BillingGateService(_FakeBillingStore(allowed=False))
    safety_store = _FakeSafetyStore()
    draft_store = _FakeDraftStore()
    review_store = _FakeReviewStore()
    contact_store = _FakeContactStore()
    sending_store = _FakeSendingStore()

    contact_store.contacts[_CONTACT] = _FakeContact(
        id=_CONTACT, tenant_id=_TENANT, email="c@test.com"
    )
    draft = await draft_store.create_draft(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        status="generated",
        subject="Test",
        body="Test",
    )

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
    with pytest.raises((AppError, BillingAccessDenied)):
        await send_gate.evaluate_gate(_principal(), draft_id=draft.id, now=_NOW)


@pytest.mark.asyncio
async def test_unauthorized_role_denied() -> None:
    """reviewer role lacks CAN_SCHEDULE_SEND → FORBIDDEN on send gate."""
    billing = BillingGateService(_FakeBillingStore(allowed=True))
    send_gate = SendGateService(
        sending_store=_FakeSendingStore(),
        draft_store=_FakeDraftStore(),
        review_store=_FakeReviewStore(),
        safety_store=_FakeSafetyStore(),
        contact_store=_FakeContactStore(),
        billing=billing,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
    )
    with pytest.raises(AppError) as exc_info:
        await send_gate.evaluate_gate(
            _principal(role="reviewer"),
            draft_id=uuid.uuid4(),
            now=_NOW,
        )
    assert exc_info.value.code == "FORBIDDEN"


def test_no_live_provider_calls() -> None:
    """Critical service modules must not import real SMTP/DNS/CRM libraries."""
    import importlib
    import sys

    forbidden_libs = {"smtplib", "dns", "twilio", "stripe", "boto3", "botocore", "requests"}
    critical_modules = [
        "app.services.send_gate",
        "app.services.mock_sender",
        "app.services.safety",
        "app.services.groundedness",
        "app.services.deliverability",
        "app.services.outcomes",
        "app.services.followup_scheduler",
    ]
    for mod_name in critical_modules:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
        else:
            mod = importlib.import_module(mod_name)
        mod_dict = vars(mod)
        for lib in forbidden_libs:
            assert (
                lib not in mod_dict
            ), f"Forbidden live-provider lib '{lib}' found imported in {mod_name}"
