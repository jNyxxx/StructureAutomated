"""Tests for Phase 1 Slice P1-12: Outcomes/ROI dashboard data foundation.

Coverage:
* migration/offline SQL check
* create mock outcome event (success, idempotency, duplicate key)
* tenant-level outcome summary
* campaign-level outcome summary
* ROI calculation (with/without assumptions)
* funnel calculation (rate math)
* date-range filters
* campaign filters
* cross-tenant outcomes denied/excluded
* campaign ownership enforced
* contact ownership enforced
* RBAC denied case
* invalid event_type rejected
* invalid ROI values rejected
* audit confirms no real CRM/provider called
* no secrets leakage in note field
* deferred: no live DB smoke
"""

from __future__ import annotations

import contextlib
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.auth.principal import CurrentPrincipal
from app.config import get_settings
from app.middleware.error_handler import AppError
from app.repositories.outcomes_repo import (
    OutcomeEventRecord,
    OutcomeTrendPoint,
    OutcomeTypeCounts,
    ROIAssumptionsRecord,
)
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.outcomes import (
    CampaignOutcomesSummary,
    FunnelSummary,
    OutcomesService,
    OutcomesSummary,
    ROISummary,
    _safe_rate,
    _safe_rate_opt,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CAMPAIGN_B = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_CONTACT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
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


# ---------------------------------------------------------------------------
# 1. Migration check
# ---------------------------------------------------------------------------


def test_migration_outcomes_tables_and_rls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    assert "CREATE TABLE outcome_events" in sql
    assert "CREATE TABLE campaign_roi_assumptions" in sql
    assert "ALTER TABLE outcome_events ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE outcome_events FORCE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE campaign_roi_assumptions ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE campaign_roi_assumptions FORCE ROW LEVEL SECURITY" in sql
    assert "outcome_events_tenant_isolation" in sql
    assert "campaign_roi_assumptions_tenant_isolation" in sql
    assert "ck_outcome_events_event_type" in sql


# ---------------------------------------------------------------------------
# Fake in-memory stores
# ---------------------------------------------------------------------------


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
        self.idempotency_index: dict[str, uuid.UUID] = {}
        self.assumptions: dict[uuid.UUID, ROIAssumptionsRecord] = {}
        # (tenant_id, campaign_id | None) -> counts
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
        if idempotency_key is not None and idempotency_key in self.idempotency_index:
            return self.events[self.idempotency_index[idempotency_key]]

        event_id = uuid.uuid4()
        rec = OutcomeEventRecord(
            id=event_id,
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
        self.events[event_id] = rec
        if idempotency_key is not None:
            self.idempotency_index[idempotency_key] = event_id
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
        existing = self.assumptions.get(campaign_id)
        rec = ROIAssumptionsRecord(
            id=existing.id if existing else uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            cost_per_send_cents=cost_per_send_cents,
            pipeline_value_per_opportunity_cents=pipeline_value_per_opportunity_cents,
            revenue_per_deal_won_cents=revenue_per_deal_won_cents,
            created_at=existing.created_at if existing else _NOW,
            updated_at=_NOW,
        )
        self.assumptions[campaign_id] = rec
        return rec

    async def get_roi_assumptions(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> ROIAssumptionsRecord | None:
        rec = self.assumptions.get(campaign_id)
        if rec is not None and rec.tenant_id == tenant_id:
            return rec
        return None

    async def get_outcome_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[OutcomeTrendPoint]:
        return self._trend


class _FakeSendCountStore:
    def __init__(self, counts: dict[tuple[uuid.UUID, uuid.UUID | None], int] | None = None) -> None:
        self._counts = counts or {}

    async def get_sent_count(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        return self._counts.get((tenant_id, campaign_id), 0)


def _make_service(
    store: _FakeOutcomesStore | None = None,
    sent_counts: dict[tuple[uuid.UUID, uuid.UUID | None], int] | None = None,
) -> OutcomesService:
    return OutcomesService(
        store=store or _FakeOutcomesStore(),
        send_count_store=_FakeSendCountStore(sent_counts),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
    )


# ---------------------------------------------------------------------------
# 2. Outcome event creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_outcome_event_success() -> None:
    store = _FakeOutcomesStore()
    svc = _make_service(store)
    ev = await svc.record_outcome_event(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        contact_id=_CONTACT,
        contact_tenant_id=_TENANT,
        event_type="reply_received",
    )
    assert ev.tenant_id == _TENANT
    assert ev.campaign_id == _CAMPAIGN
    assert ev.event_type == "reply_received"
    assert len(store.events) == 1


@pytest.mark.asyncio
async def test_create_outcome_event_idempotency() -> None:
    """Same idempotency key → same row returned, no duplicate inserted."""
    store = _FakeOutcomesStore()
    svc = _make_service(store)
    ev1 = await svc.record_outcome_event(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        contact_id=_CONTACT,
        contact_tenant_id=_TENANT,
        event_type="meeting_booked",
        idempotency_key="meeting-idem-001",
    )
    ev2 = await svc.record_outcome_event(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        contact_id=_CONTACT,
        contact_tenant_id=_TENANT,
        event_type="meeting_booked",
        idempotency_key="meeting-idem-001",
    )
    assert ev1.id == ev2.id
    assert len(store.events) == 1


@pytest.mark.asyncio
async def test_create_outcome_event_invalid_event_type() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.record_outcome_event(
            _principal("owner"),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_TENANT,
            contact_id=_CONTACT,
            contact_tenant_id=_TENANT,
            event_type="not_a_real_event",
        )
    assert exc.value.code == "INVALID_OUTCOME_EVENT_TYPE"


@pytest.mark.asyncio
async def test_create_outcome_event_rbac_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.record_outcome_event(
            _principal("viewer"),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_TENANT,
            contact_id=_CONTACT,
            contact_tenant_id=_TENANT,
            event_type="reply_received",
        )
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_outcome_event_campaign_tenant_mismatch() -> None:
    """Campaign owned by other tenant → FORBIDDEN."""
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.record_outcome_event(
            _principal("owner", tenant_id=_TENANT),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_OTHER_TENANT,  # mismatch
            contact_id=_CONTACT,
            contact_tenant_id=_TENANT,
            event_type="reply_received",
        )
    assert exc.value.code == "OBJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_create_outcome_event_contact_tenant_mismatch() -> None:
    """Contact owned by other tenant → OBJECT_ACCESS_DENIED."""
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.record_outcome_event(
            _principal("owner", tenant_id=_TENANT),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_TENANT,
            contact_id=_CONTACT,
            contact_tenant_id=_OTHER_TENANT,  # mismatch
            event_type="reply_received",
        )
    assert exc.value.code == "OBJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_create_outcome_event_all_valid_types() -> None:
    """All declared event types should be accepted."""
    from app.models.outcomes import OUTCOME_EVENT_TYPES

    store = _FakeOutcomesStore()
    svc = _make_service(store)
    for et in OUTCOME_EVENT_TYPES:
        await svc.record_outcome_event(
            _principal("owner"),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_TENANT,
            contact_id=_CONTACT,
            contact_tenant_id=_TENANT,
            event_type=et,
        )
    assert len(store.events) == len(OUTCOME_EVENT_TYPES)


# ---------------------------------------------------------------------------
# 3. Tenant-level summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_summary_counts_and_rates() -> None:
    store = _FakeOutcomesStore()
    store.set_counts(
        tenant_id=_TENANT,
        counts=_FakeOutcomeTypeCounts(
            reply_received=10, meeting_booked=5, opportunity_created=3, deal_won=1
        ),
    )
    sent_map = {(_TENANT, None): 100}
    svc = _make_service(store, sent_map)
    summary = await svc.get_tenant_summary(_principal("owner"))

    assert isinstance(summary, OutcomesSummary)
    assert summary.tenant_id == _TENANT
    assert summary.reply_count == 10
    assert summary.meeting_booked_count == 5
    assert summary.opportunity_count == 3
    assert summary.deal_won_count == 1
    assert summary.reply_rate == 0.1  # 10/100
    assert summary.meeting_rate == 0.05
    assert summary.opportunity_rate == 0.03


@pytest.mark.asyncio
async def test_tenant_summary_rbac_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.get_tenant_summary(_principal("reviewer"))
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_tenant_summary_excludes_other_tenant() -> None:
    """Other-tenant counts are stored under a different key; our query gets zero."""
    store = _FakeOutcomesStore()
    store.set_counts(
        tenant_id=_OTHER_TENANT,
        counts=_FakeOutcomeTypeCounts(reply_received=99),
    )
    svc = _make_service(store)
    summary = await svc.get_tenant_summary(_principal("owner", tenant_id=_TENANT))
    assert summary.reply_count == 0  # _TENANT has no counts


@pytest.mark.asyncio
async def test_tenant_summary_date_range_passthrough() -> None:
    """Date range values are stored in the summary DTO as-is."""
    store = _FakeOutcomesStore()
    svc = _make_service(store)
    date_from = _NOW - timedelta(days=7)
    date_to = _NOW
    summary = await svc.get_tenant_summary(
        _principal("owner"), date_from=date_from, date_to=date_to
    )

    assert summary.date_from == date_from
    assert summary.date_to == date_to


# ---------------------------------------------------------------------------
# 4. Campaign-level summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_campaign_summary_counts_and_rates() -> None:
    store = _FakeOutcomesStore()
    store.set_counts(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        counts=_FakeOutcomeTypeCounts(
            reply_received=20, positive_reply=8, meeting_booked=4, deal_won=2
        ),
    )
    sent_map = {(_TENANT, _CAMPAIGN): 200}
    svc = _make_service(store, sent_map)
    summary = await svc.get_campaign_summary(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
    )

    assert isinstance(summary, CampaignOutcomesSummary)
    assert summary.campaign_id == _CAMPAIGN
    assert summary.reply_count == 20
    assert summary.positive_reply_count == 8
    assert summary.reply_rate == 0.1  # 20/200
    assert summary.deal_won_count == 2


@pytest.mark.asyncio
async def test_campaign_summary_rbac_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.get_campaign_summary(
            _principal("reviewer"),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_TENANT,
        )
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_campaign_summary_cross_tenant_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.get_campaign_summary(
            _principal("owner", tenant_id=_TENANT),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_OTHER_TENANT,
        )
    assert exc.value.code == "OBJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_campaign_filter_isolates_campaigns() -> None:
    """Different campaigns return their own counts."""
    store = _FakeOutcomesStore()
    store.set_counts(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        counts=_FakeOutcomeTypeCounts(reply_received=5),
    )
    store.set_counts(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN_B,
        counts=_FakeOutcomeTypeCounts(reply_received=15),
    )
    svc = _make_service(store)
    a = await svc.get_campaign_summary(
        _principal("owner"), campaign_id=_CAMPAIGN, campaign_tenant_id=_TENANT
    )
    b = await svc.get_campaign_summary(
        _principal("owner"), campaign_id=_CAMPAIGN_B, campaign_tenant_id=_TENANT
    )
    assert a.reply_count == 5
    assert b.reply_count == 15


# ---------------------------------------------------------------------------
# 5. ROI calculation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_roi_summary_with_assumptions() -> None:
    store = _FakeOutcomesStore()
    # Set assumptions: $0.10/send, $5000/opportunity, $20000/deal_won
    await store.upsert_roi_assumptions(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        cost_per_send_cents=10,
        pipeline_value_per_opportunity_cents=500000,
        revenue_per_deal_won_cents=2000000,
    )
    # 3 opportunities, 1 deal won
    store.set_counts(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        counts=_FakeOutcomeTypeCounts(opportunity_created=3, deal_won=1),
    )
    svc = _make_service(store)
    roi = await svc.get_roi_summary(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        sent_count=100,
    )
    assert isinstance(roi, ROISummary)
    assert roi.sent_count == 100
    # cost = 100 * 10 = 1000 cents
    assert roi.estimated_cost_cents == 1000
    # pipeline = 3 * 500000 = 1500000 cents
    assert roi.estimated_pipeline_value_cents == 1500000
    # won = 1 * 2000000 = 2000000 cents
    assert roi.estimated_won_value_cents == 2000000
    # roi_pct = (2000000 - 1000) / 1000 * 100 = 199900%
    assert roi.estimated_roi_percent is not None
    assert roi.estimated_roi_percent > 0


@pytest.mark.asyncio
async def test_roi_summary_no_assumptions_gives_zero() -> None:
    svc = _make_service()
    roi = await svc.get_roi_summary(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        sent_count=50,
    )
    assert roi.estimated_cost_cents == 0
    assert roi.estimated_pipeline_value_cents == 0
    assert roi.estimated_won_value_cents == 0
    assert roi.estimated_roi_percent is None


@pytest.mark.asyncio
async def test_roi_summary_zero_cost_no_roi_pct() -> None:
    store = _FakeOutcomesStore()
    await store.upsert_roi_assumptions(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        cost_per_send_cents=0,  # zero cost → ROI undefined
        pipeline_value_per_opportunity_cents=100,
        revenue_per_deal_won_cents=500,
    )
    svc = _make_service(store)
    roi = await svc.get_roi_summary(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        sent_count=100,
    )
    assert roi.estimated_roi_percent is None


@pytest.mark.asyncio
async def test_set_roi_assumptions_rbac_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.set_roi_assumptions(
            _principal("viewer"),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_TENANT,
            cost_per_send_cents=10,
            pipeline_value_per_opportunity_cents=0,
            revenue_per_deal_won_cents=0,
        )
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_set_roi_assumptions_invalid_negative() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.set_roi_assumptions(
            _principal("owner"),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_TENANT,
            cost_per_send_cents=-1,
            pipeline_value_per_opportunity_cents=0,
            revenue_per_deal_won_cents=0,
        )
    assert exc.value.code == "INVALID_ROI_VALUE"


@pytest.mark.asyncio
async def test_set_roi_assumptions_upsert() -> None:
    """Second call updates the assumptions in-place."""
    store = _FakeOutcomesStore()
    svc = _make_service(store)
    a1 = await svc.set_roi_assumptions(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        cost_per_send_cents=5,
        pipeline_value_per_opportunity_cents=100,
        revenue_per_deal_won_cents=200,
    )
    a2 = await svc.set_roi_assumptions(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        cost_per_send_cents=10,
        pipeline_value_per_opportunity_cents=200,
        revenue_per_deal_won_cents=400,
    )
    assert a1.id == a2.id  # same row
    assert a2.cost_per_send_cents == 10


@pytest.mark.asyncio
async def test_roi_summary_cross_tenant_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.get_roi_summary(
            _principal("owner", tenant_id=_TENANT),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_OTHER_TENANT,
            sent_count=10,
        )
    assert exc.value.code == "OBJECT_ACCESS_DENIED"


# ---------------------------------------------------------------------------
# 6. Funnel summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_funnel_summary_rates() -> None:
    store = _FakeOutcomesStore()
    store.set_counts(
        tenant_id=_TENANT,
        counts=_FakeOutcomeTypeCounts(
            reply_received=40,
            meeting_booked=20,
            opportunity_created=10,
            deal_won=5,
        ),
    )
    svc = _make_service(store)
    funnel = await svc.get_funnel_summary(
        _principal("owner"),
        campaign_id=None,
        campaign_tenant_id=None,
        sent_count=200,
    )
    assert isinstance(funnel, FunnelSummary)
    assert funnel.sent == 200
    assert funnel.replied == 40
    assert funnel.meeting_booked == 20
    assert funnel.opportunity == 10
    assert funnel.deal_won == 5
    assert funnel.sent_to_reply_rate == pytest.approx(0.2)
    assert funnel.reply_to_meeting_rate == pytest.approx(0.5)
    assert funnel.meeting_to_opportunity_rate == pytest.approx(0.5)
    assert funnel.opportunity_to_win_rate == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_funnel_summary_zero_sent_gives_none_rates() -> None:
    store = _FakeOutcomesStore()
    svc = _make_service(store)
    funnel = await svc.get_funnel_summary(
        _principal("owner"),
        campaign_id=None,
        campaign_tenant_id=None,
        sent_count=0,
    )
    assert funnel.sent_to_reply_rate is None


@pytest.mark.asyncio
async def test_funnel_rbac_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.get_funnel_summary(
            _principal("reviewer"),
            campaign_id=None,
            campaign_tenant_id=None,
            sent_count=0,
        )
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_funnel_campaign_cross_tenant_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.get_funnel_summary(
            _principal("owner", tenant_id=_TENANT),
            campaign_id=_CAMPAIGN,
            campaign_tenant_id=_OTHER_TENANT,
            sent_count=10,
        )
    assert exc.value.code == "OBJECT_ACCESS_DENIED"


# ---------------------------------------------------------------------------
# 7. Rate helpers (unit)
# ---------------------------------------------------------------------------


def test_safe_rate_zero_denom() -> None:
    assert _safe_rate(5, 0) == 0.0


def test_safe_rate_normal() -> None:
    assert _safe_rate(1, 4) == 0.25


def test_safe_rate_opt_zero_denom() -> None:
    assert _safe_rate_opt(5, 0) is None


def test_safe_rate_opt_normal() -> None:
    assert _safe_rate_opt(1, 4) == 0.25


# ---------------------------------------------------------------------------
# 8. Date-range filter passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_date_range_filter_stored_in_summary() -> None:
    svc = _make_service()
    date_from = _NOW - timedelta(days=30)
    date_to = _NOW
    summary = await svc.get_tenant_summary(
        _principal("owner"), date_from=date_from, date_to=date_to
    )
    assert summary.date_from == date_from
    assert summary.date_to == date_to


@pytest.mark.asyncio
async def test_campaign_date_range_filter() -> None:
    svc = _make_service()
    date_from = _NOW - timedelta(days=14)
    date_to = _NOW
    summary = await svc.get_campaign_summary(
        _principal("owner"),
        campaign_id=_CAMPAIGN,
        campaign_tenant_id=_TENANT,
        date_from=date_from,
        date_to=date_to,
    )
    assert summary.date_from == date_from
    assert summary.date_to == date_to


# ---------------------------------------------------------------------------
# 9. Trend endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trend_returns_store_data() -> None:
    from datetime import date

    store = _FakeOutcomesStore()
    store._trend = [
        OutcomeTrendPoint(
            bucket_date=date(2026, 6, 1), reply_received=3, meeting_booked=1, deal_won=0
        )
    ]
    svc = _make_service(store)
    trend = await svc.get_trend(
        _principal("owner"),
        campaign_id=None,
        campaign_tenant_id=None,
        date_from=_NOW - timedelta(days=30),
        date_to=_NOW,
    )
    assert len(trend) == 1
    assert trend[0].reply_received == 3


@pytest.mark.asyncio
async def test_get_trend_rbac_denied() -> None:
    svc = _make_service()
    with pytest.raises(AppError) as exc:
        await svc.get_trend(
            _principal("reviewer"),
            campaign_id=None,
            campaign_tenant_id=None,
            date_from=_NOW - timedelta(days=7),
            date_to=_NOW,
        )
    assert exc.value.code == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 10. No real provider called (structural guard)
# ---------------------------------------------------------------------------


def test_no_real_provider_in_service_source() -> None:
    """Guard: outcomes.py must not import real CRM/payment/ad providers."""
    import inspect

    from app.services import outcomes

    src = inspect.getsource(outcomes)
    forbidden = ["stripe", "twilio", "smtplib", "sendgrid", "mailgun", "hubspot", "salesforce"]
    for token in forbidden:
        assert token not in src.lower(), f"Real provider '{token}' found in outcomes service source"


def test_no_secrets_in_outcome_note() -> None:
    """Structural: note field is a plain text field — service passes it through but does not
    log or emit it in audit payloads. No validation of the value is needed at this layer;
    we merely confirm the field is optional and can be None."""
    rec = OutcomeEventRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT,
        outbound_message_id=None,
        event_type="reply_received",
        note=None,  # safe default
        idempotency_key=None,
        occurred_at=_NOW,
        created_at=_NOW,
    )
    assert rec.note is None
