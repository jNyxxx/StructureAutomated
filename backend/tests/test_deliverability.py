"""Tests for Phase 1 Slice P1-11: Deliverability dashboard data foundation."""

from __future__ import annotations

import ast
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.deliverability_repo import (
    DeliverabilityTrendPoint,
    FollowupCounts,
    GateCounts,
    OutboundCounts,
)
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.deliverability import (
    _MOCK_BOUNCE_RATE,
    _MOCK_COMPLAINT_RATE,
    _MOCK_OPEN_RATE,
    _MOCK_REPLY_RATE,
    CampaignDeliverabilitySummary,
    DeliverabilityService,
    DeliverabilitySummary,
    MailboxHealthSummary,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_CAMPAIGN_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_ACTOR = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_NOW = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


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
# In-memory fake store
# ---------------------------------------------------------------------------


@dataclass
class _FakeOutboundCounts:
    sent: int = 0
    blocked: int = 0


@dataclass
class _FakeGateCounts:
    duplicate_denied: int = 0
    suppressed: int = 0
    safety_denied: int = 0
    throttled: int = 0


@dataclass
class _FakeFollowupCounts:
    followup_sent: int = 0
    followup_skipped: int = 0


class _FakeStore:
    """In-memory deliverability store. Filters by tenant_id and campaign_id."""

    def __init__(
        self,
        *,
        outbound: dict[uuid.UUID, _FakeOutboundCounts] | None = None,
        gates: dict[uuid.UUID, _FakeGateCounts] | None = None,
        followups: dict[uuid.UUID, _FakeFollowupCounts] | None = None,
        trend: list[DeliverabilityTrendPoint] | None = None,
    ) -> None:
        # keyed by (tenant_id, campaign_id or None)
        self._outbound: dict[tuple[uuid.UUID, uuid.UUID | None], _FakeOutboundCounts] = {}
        self._gates: dict[tuple[uuid.UUID, uuid.UUID | None], _FakeGateCounts] = {}
        self._followups: dict[tuple[uuid.UUID, uuid.UUID | None], _FakeFollowupCounts] = {}
        self._trend: list[DeliverabilityTrendPoint] = trend or []

        if outbound:
            for t_id, om_c in outbound.items():
                self._outbound[(t_id, None)] = om_c
        if gates:
            for t_id, g_c in gates.items():
                self._gates[(t_id, None)] = g_c
        if followups:
            for t_id, f_c in followups.items():
                self._followups[(t_id, None)] = f_c

    def set_campaign(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        outbound: _FakeOutboundCounts | None = None,
        gates: _FakeGateCounts | None = None,
        followups: _FakeFollowupCounts | None = None,
    ) -> None:
        if outbound:
            self._outbound[(tenant_id, campaign_id)] = outbound
        if gates:
            self._gates[(tenant_id, campaign_id)] = gates
        if followups:
            self._followups[(tenant_id, campaign_id)] = followups

    async def get_outbound_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> OutboundCounts:
        raw = self._outbound.get((tenant_id, campaign_id), _FakeOutboundCounts())
        return OutboundCounts(sent=raw.sent, blocked=raw.blocked)

    async def get_gate_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> GateCounts:
        raw = self._gates.get((tenant_id, campaign_id), _FakeGateCounts())
        return GateCounts(
            duplicate_denied=raw.duplicate_denied,
            suppressed=raw.suppressed,
            safety_denied=raw.safety_denied,
            throttled=raw.throttled,
        )

    async def get_followup_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> FollowupCounts:
        raw = self._followups.get((tenant_id, campaign_id), _FakeFollowupCounts())
        return FollowupCounts(
            followup_sent=raw.followup_sent,
            followup_skipped=raw.followup_skipped,
        )

    async def get_trend(
        self,
        *,
        tenant_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> list[DeliverabilityTrendPoint]:
        return list(self._trend)


def _service(store: _FakeStore | None = None) -> DeliverabilityService:
    return DeliverabilityService(
        store=store or _FakeStore(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
    )


# ---------------------------------------------------------------------------
# Tests: tenant-level summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_summary_sent_and_blocked() -> None:
    store = _FakeStore(
        outbound={_TENANT: _FakeOutboundCounts(sent=10, blocked=3)},
    )
    svc = _service(store)
    result = await svc.get_tenant_summary(_principal())
    assert isinstance(result, DeliverabilitySummary)
    assert result.tenant_id == _TENANT
    assert result.sent == 10
    assert result.blocked == 3


@pytest.mark.asyncio
async def test_tenant_summary_followup_counted() -> None:
    store = _FakeStore(
        outbound={_TENANT: _FakeOutboundCounts(sent=5)},
        followups={_TENANT: _FakeFollowupCounts(followup_sent=4, followup_skipped=1)},
    )
    svc = _service(store)
    result = await svc.get_tenant_summary(_principal())
    assert result.followup_sent == 4
    assert result.followup_skipped == 1


@pytest.mark.asyncio
async def test_tenant_summary_gate_reasons_counted() -> None:
    store = _FakeStore(
        gates={
            _TENANT: _FakeGateCounts(
                duplicate_denied=2,
                suppressed=3,
                safety_denied=1,
                throttled=1,
            )
        },
    )
    svc = _service(store)
    result = await svc.get_tenant_summary(_principal())
    assert result.duplicate_denied == 2
    assert result.suppressed == 3
    assert result.safety_denied == 1
    assert result.throttled == 1


@pytest.mark.asyncio
async def test_tenant_summary_mock_engagement_rates() -> None:
    sent = 100
    store = _FakeStore(outbound={_TENANT: _FakeOutboundCounts(sent=sent)})
    svc = _service(store)
    result = await svc.get_tenant_summary(_principal())
    assert result.mock_bounced == int(sent * _MOCK_BOUNCE_RATE)
    assert result.mock_complained == int(sent * _MOCK_COMPLAINT_RATE)
    assert result.mock_opened == int(sent * _MOCK_OPEN_RATE)
    assert result.mock_replied == int(sent * _MOCK_REPLY_RATE)


@pytest.mark.asyncio
async def test_tenant_summary_zero_sent_zero_engagement() -> None:
    store = _FakeStore(outbound={_TENANT: _FakeOutboundCounts(sent=0)})
    svc = _service(store)
    result = await svc.get_tenant_summary(_principal())
    assert result.mock_bounced == 0
    assert result.mock_opened == 0


# ---------------------------------------------------------------------------
# Tests: campaign-level summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_campaign_summary_scoped() -> None:
    store = _FakeStore()
    store.set_campaign(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN_A,
        outbound=_FakeOutboundCounts(sent=7, blocked=1),
        followups=_FakeFollowupCounts(followup_sent=2),
    )
    store.set_campaign(
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN_B,
        outbound=_FakeOutboundCounts(sent=99),
    )
    svc = _service(store)
    result = await svc.get_campaign_summary(
        _principal(),
        campaign_id=_CAMPAIGN_A,
        campaign_tenant_id=_TENANT,
    )
    assert isinstance(result, CampaignDeliverabilitySummary)
    assert result.campaign_id == _CAMPAIGN_A
    assert result.sent == 7
    assert result.blocked == 1
    assert result.followup_sent == 2


# ---------------------------------------------------------------------------
# Tests: date range filtering (store honours the kwargs — tested at service layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_date_range_echoed_in_result() -> None:
    date_from = _NOW - timedelta(days=7)
    date_to = _NOW
    store = _FakeStore(outbound={_TENANT: _FakeOutboundCounts(sent=5)})
    svc = _service(store)
    result = await svc.get_tenant_summary(_principal(), date_from=date_from, date_to=date_to)
    assert result.date_from == date_from
    assert result.date_to == date_to


# ---------------------------------------------------------------------------
# Tests: RBAC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rbac_denied_tenant_summary() -> None:
    svc = _service()
    with pytest.raises(AppError):
        await svc.get_tenant_summary(_principal(role="reviewer"))


@pytest.mark.asyncio
async def test_rbac_denied_campaign_summary() -> None:
    svc = _service()
    with pytest.raises(AppError):
        await svc.get_campaign_summary(
            _principal(role="reviewer"),
            campaign_id=_CAMPAIGN_A,
            campaign_tenant_id=_TENANT,
        )


def test_rbac_denied_mailbox_health() -> None:
    svc = _service()
    with pytest.raises(AppError):
        svc.get_mailbox_health(_principal(role="reviewer"))


# ---------------------------------------------------------------------------
# Tests: object authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_campaign_object_auth_denied_cross_tenant() -> None:
    """Campaign belonging to another tenant → OBJECT_ACCESS_DENIED."""
    svc = _service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_campaign_summary(
            _principal(tenant_id=_TENANT),
            campaign_id=_CAMPAIGN_A,
            campaign_tenant_id=_OTHER_TENANT,
        )
    assert exc_info.value.code == "OBJECT_ACCESS_DENIED"


# ---------------------------------------------------------------------------
# Tests: cross-tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_records_excluded() -> None:
    """Other-tenant data must never appear in a tenant's summary."""
    store = _FakeStore(
        outbound={
            _TENANT: _FakeOutboundCounts(sent=5),
            _OTHER_TENANT: _FakeOutboundCounts(sent=999),
        }
    )
    svc = _service(store)
    result = await svc.get_tenant_summary(_principal(tenant_id=_TENANT))
    # The fake store returns exactly what's keyed by tenant — no bleed through
    assert result.sent == 5
    assert result.tenant_id == _TENANT


# ---------------------------------------------------------------------------
# Tests: mailbox health
# ---------------------------------------------------------------------------


def test_mailbox_health_deterministic() -> None:
    svc = _service()
    principal = _principal()
    h1 = svc.get_mailbox_health(principal)
    h2 = svc.get_mailbox_health(principal)
    assert isinstance(h1, MailboxHealthSummary)
    assert h1 == h2


def test_mailbox_health_fields_valid() -> None:
    svc = _service()
    result = svc.get_mailbox_health(_principal())
    assert result.tenant_id == _TENANT
    assert result.dkim_valid is True
    assert result.spf_valid is True
    assert result.dmarc_valid is True
    assert 70 <= result.reputation_score <= 99
    assert "example.com" in result.mock_domain


def test_mailbox_health_no_real_dns() -> None:
    """Ensure get_mailbox_health never performs network I/O."""
    import socket

    original_getaddrinfo = socket.getaddrinfo

    def _blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network call detected in get_mailbox_health")

    socket.getaddrinfo = _blocked  # type: ignore[assignment]
    try:
        svc = _service()
        svc.get_mailbox_health(_principal())
    finally:
        socket.getaddrinfo = original_getaddrinfo


# ---------------------------------------------------------------------------
# Tests: trend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trend_returns_sorted_points() -> None:
    from datetime import date

    points = [
        DeliverabilityTrendPoint(bucket_date=date(2026, 6, 21), sent=3, blocked=1, followup_sent=0),
        DeliverabilityTrendPoint(bucket_date=date(2026, 6, 22), sent=5, blocked=0, followup_sent=2),
    ]
    store = _FakeStore(trend=points)
    svc = _service(store)
    result = await svc.get_trend(
        _principal(),
        date_from=_NOW - timedelta(days=7),
        date_to=_NOW,
    )
    assert len(result) == 2
    assert result[0].bucket_date < result[1].bucket_date
    assert result[0].sent == 3
    assert result[1].followup_sent == 2


@pytest.mark.asyncio
async def test_trend_rbac_denied() -> None:
    svc = _service()
    with pytest.raises(AppError):
        await svc.get_trend(
            _principal(role="reviewer"),
            date_from=_NOW - timedelta(days=7),
            date_to=_NOW,
        )


# ---------------------------------------------------------------------------
# Tests: no real provider, no secrets, no frontend, no migration
# ---------------------------------------------------------------------------


def test_no_real_provider_imports() -> None:
    """Deliverability service must not import smtp/dns/twilio/stripe libs."""
    import importlib
    import sys

    # Reload to get fresh module state
    mod_name = "app.services.deliverability"
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
    else:
        mod = importlib.import_module(mod_name)

    forbidden = {"smtplib", "dns", "twilio", "stripe", "boto3", "botocore"}
    for dep in forbidden:
        assert dep not in dir(mod), f"Forbidden dependency found: {dep}"


def test_no_secrets_in_mailbox_output() -> None:
    """MailboxHealthSummary fields must not contain token/key/secret patterns."""
    svc = _service()
    result = svc.get_mailbox_health(_principal())
    for field_val in (result.mock_domain,):
        lowered = field_val.lower()
        for bad in ("secret", "token", "key", "password", "api_"):
            assert bad not in lowered, f"Sensitive pattern '{bad}' in output"


def test_no_deliverability_migration_created() -> None:
    """P1-11 must not create a new migration — all data comes from existing tables."""
    migration_files = list(_MIGRATIONS_DIR.glob("*deliverability*"))
    assert not migration_files, f"Unexpected deliverability migration created: {migration_files}"


def test_deliverability_backend_is_decoupled_from_frontend() -> None:
    """Backend deliverability code must stay decoupled from later frontend shells."""
    backend_app_dir = Path(__file__).resolve().parents[1] / "app"
    backend_deliverability_files = list(backend_app_dir.rglob("*deliverabilit*.py"))
    assert backend_deliverability_files, "Expected backend deliverability files to exist"

    for path in backend_deliverability_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
                assert not any(
                    name.startswith("frontend") for name in imported
                ), f"Backend file imports frontend module: {path}"
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    "frontend"
                ), f"Backend file imports frontend module: {path}"
