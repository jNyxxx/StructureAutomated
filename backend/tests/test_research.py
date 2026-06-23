"""Tests for Phase 1 Slice P1-03 Research task pipeline (mock research only)."""

import contextlib
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config

from app.auth.principal import CurrentPrincipal
from app.config import get_settings
from app.services.authz import (
    AuthorizationError,
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
from app.services.campaign import CampaignContactRecord, CampaignRecord
from app.services.idempotency import IdempotencyOutcome, IdempotencyState
from app.services.research import (
    ResearchArtifactRecord,
    ResearchRunRecord,
    ResearchService,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT_1 = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc1111")
_CONTACT_2 = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc2222")
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


class _IdempotencyGate:
    def __init__(self, outcome: IdempotencyOutcome | None = None) -> None:
        self.outcome = outcome or IdempotencyOutcome(IdempotencyState.NEW)
        self.begin_calls: list[dict[str, Any]] = []
        self.complete_calls: list[dict[str, Any]] = []

    async def begin(
        self,
        *,
        key: str,
        request_payload: Any,
        now: datetime,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> IdempotencyOutcome:
        self.begin_calls.append(
            {
                "key": key,
                "request_payload": request_payload,
                "tenant_id": tenant_id,
                "actor_user_id": actor_user_id,
            }
        )
        return self.outcome

    async def complete(
        self,
        *,
        key: str,
        response_payload: Any,
        status_code: int,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        self.complete_calls.append(
            {
                "key": key,
                "response_payload": response_payload,
                "status_code": status_code,
                "tenant_id": tenant_id,
            }
        )


class _FakeResearchStore:
    def __init__(self) -> None:
        self.runs: dict[uuid.UUID, ResearchRunRecord] = {}
        self.artifacts: dict[uuid.UUID, ResearchArtifactRecord] = {}
        self.contacts: dict[uuid.UUID, Any] = {}

    async def create_run(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None,
        status: str,
        queued_count: int,
    ) -> ResearchRunRecord:
        run = ResearchRunRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            created_by_user_id=created_by_user_id,
            status=status,
            queued_count=queued_count,
            processed_count=0,
            failed_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.runs[run.id] = run
        return run

    async def get_run(self, *, tenant_id: uuid.UUID, run_id: uuid.UUID) -> ResearchRunRecord | None:
        run = self.runs.get(run_id)
        if run is not None and run.tenant_id == tenant_id:
            return run
        return None

    async def update_run(
        self,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        status: str | None = None,
        processed_count: int | None = None,
        failed_count: int | None = None,
    ) -> ResearchRunRecord | None:
        run = await self.get_run(tenant_id=tenant_id, run_id=run_id)
        if run is None:
            return None
        updated = ResearchRunRecord(
            id=run.id,
            tenant_id=run.tenant_id,
            campaign_id=run.campaign_id,
            created_by_user_id=run.created_by_user_id,
            status=status if status is not None else run.status,
            queued_count=run.queued_count,
            processed_count=(
                processed_count if processed_count is not None else run.processed_count
            ),
            failed_count=failed_count if failed_count is not None else run.failed_count,
            created_at=run.created_at,
            updated_at=datetime.now(UTC),
        )
        self.runs[run.id] = updated
        return updated

    async def increment_run_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        processed: int = 0,
        failed: int = 0,
    ) -> ResearchRunRecord | None:
        run = await self.get_run(tenant_id=tenant_id, run_id=run_id)
        if run is None:
            return None
        updated = ResearchRunRecord(
            id=run.id,
            tenant_id=run.tenant_id,
            campaign_id=run.campaign_id,
            created_by_user_id=run.created_by_user_id,
            status=run.status,
            queued_count=run.queued_count,
            processed_count=run.processed_count + processed,
            failed_count=run.failed_count + failed,
            created_at=run.created_at,
            updated_at=datetime.now(UTC),
        )
        self.runs[run.id] = updated
        return updated

    async def create_artifact(
        self,
        *,
        tenant_id: uuid.UUID,
        research_run_id: uuid.UUID,
        contact_id: uuid.UUID,
        findings: dict[str, Any],
    ) -> ResearchArtifactRecord:
        art = ResearchArtifactRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            research_run_id=research_run_id,
            contact_id=contact_id,
            findings=findings,
            created_at=datetime.now(UTC),
        )
        self.artifacts[art.id] = art
        return art

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any:
        contact = self.contacts.get(contact_id)
        if contact is not None and contact.tenant_id == tenant_id:
            return contact
        return None


@dataclass
class _FakeContact:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str | None
    company_name: str | None
    full_name: str | None


class _FakeResearchCampaignStore:
    def __init__(self) -> None:
        self.campaigns: dict[uuid.UUID, CampaignRecord] = {}
        self.contacts: dict[uuid.UUID, CampaignContactRecord] = {}

    async def get_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> CampaignRecord | None:
        campaign = self.campaigns.get(campaign_id)
        if campaign is not None and campaign.tenant_id == tenant_id:
            return campaign
        return None

    async def list_campaign_contacts(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> list[CampaignContactRecord]:
        return [
            c
            for c in self.contacts.values()
            if c.campaign_id == campaign_id and c.tenant_id == tenant_id
        ]

    async def set_campaign_contact_status(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord | None:
        for c in self.contacts.values():
            if (
                c.campaign_id == campaign_id
                and c.contact_id == contact_id
                and c.tenant_id == tenant_id
            ):
                updated = CampaignContactRecord(
                    id=c.id,
                    tenant_id=c.tenant_id,
                    campaign_id=c.campaign_id,
                    contact_id=c.contact_id,
                    status=status,
                )
                self.contacts[c.id] = updated
                return updated
        return None


class _FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    async def enqueue(
        self,
        *,
        tenant_id: uuid.UUID,
        job_type: str,
        payload: dict[str, Any],
        now: datetime,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
    ) -> Any:
        job = {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "job_type": job_type,
            "payload": payload,
            "now": now,
            "max_attempts": max_attempts,
            "idempotency_key": idempotency_key,
        }
        self.jobs.append(job)
        return job


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


class _FakeJob:
    def __init__(self, tenant_id: uuid.UUID, payload: dict[str, Any]) -> None:
        self.tenant_id = tenant_id
        self.payload = payload


class _FakeScalarResult:
    def __init__(self, val: Any) -> None:
        self._val = val

    def scalar(self) -> Any:
        return self._val


class _FakeAsyncConnection:
    def __init__(self, current_tenant_val: str | None = None) -> None:
        self.current_tenant_val = current_tenant_val
        self.executed_queries: list[Any] = []

    async def execute(self, stmt: Any, *args: Any, **kwargs: Any) -> Any:
        self.executed_queries.append((stmt, args, kwargs))
        return _FakeScalarResult(self.current_tenant_val)


# 1. Migration/offline SQL check
def _render_offline_sql() -> str:
    cfg = Config(str(_ALEMBIC_INI))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(cfg, "head", sql=True)
    return buffer.getvalue()


def test_offline_sql_render_includes_research_runs_and_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        sql = _render_offline_sql()
    finally:
        get_settings.cache_clear()

    assert "CREATE TABLE research_runs" in sql
    assert "CREATE TABLE research_artifacts" in sql
    assert "ALTER TABLE research_runs ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE research_runs FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY research_runs_tenant_isolation ON research_runs" in sql
    assert "ALTER TABLE research_artifacts ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE research_artifacts FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY research_artifacts_tenant_isolation ON research_artifacts" in sql


# 2. Research run creation and standard flow tests
@pytest.mark.asyncio
async def test_start_research_run_success() -> None:
    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()
    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    # Set up campaign
    campaign = CampaignRecord(
        id=_CAMPAIGN,
        tenant_id=_TENANT,
        created_by_user_id=_ACTOR,
        name="Test Campaign",
        description="Desc",
        goal="Goal",
        target_segment="CRE",
        notes=None,
        status="ready",
    )
    camp_store.campaigns[_CAMPAIGN] = campaign

    # Add selected contacts
    contact1 = CampaignContactRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT_1,
        status="selected",
    )
    contact2 = CampaignContactRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT_2,
        status="selected",
    )
    camp_store.contacts[contact1.id] = contact1
    camp_store.contacts[contact2.id] = contact2

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
        audit_record=record_audit,
    )

    res = await service.start_research_run(principal=_principal(), campaign_id=_CAMPAIGN, now=_NOW)

    assert res.run is not None
    assert res.run.queued_count == 2
    assert res.run.status == "pending"

    # Verify only selected campaign contacts are queued
    assert len(queue.jobs) == 2
    assert queue.jobs[0]["payload"]["contact_id"] == str(_CONTACT_1)
    assert queue.jobs[1]["payload"]["contact_id"] == str(_CONTACT_2)

    # Queue job enqueue uses deterministic key
    assert queue.jobs[0]["idempotency_key"] == f"research_job:{res.run.id}:{_CONTACT_1}"

    # Audit event research.run_started emitted
    assert len(audit_events) == 1
    assert audit_events[0]["event_type"] == "research.run_started"
    assert audit_events[0]["tenant_id"] == _TENANT


# 3. Denied / Authorization cases tests
@pytest.mark.asyncio
async def test_start_research_run_allowed_and_denied_roles() -> None:
    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()

    campaign = CampaignRecord(
        id=_CAMPAIGN,
        tenant_id=_TENANT,
        created_by_user_id=_ACTOR,
        name="Test Campaign",
        description="Desc",
        goal="Goal",
        target_segment="CRE",
        notes=None,
        status="ready",
    )
    camp_store.campaigns[_CAMPAIGN] = campaign

    contact1 = CampaignContactRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT_1,
        status="selected",
    )
    camp_store.contacts[contact1.id] = contact1

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
    )

    # Allowed roles: owner, admin, marketer should succeed
    for role in ("owner", "admin", "marketer"):
        queue.jobs.clear()
        res = await service.start_research_run(
            principal=_principal(role), campaign_id=_CAMPAIGN, now=_NOW
        )
        assert res.run is not None
        assert len(queue.jobs) == 1

    # Denied roles: reviewer, viewer, billing_admin, support should raise AuthorizationError
    for role in ("reviewer", "viewer", "billing_admin", "support"):
        with pytest.raises(AuthorizationError):
            await service.start_research_run(
                principal=_principal(role), campaign_id=_CAMPAIGN, now=_NOW
            )


def test_rbac_service_unknown_permission_denies_by_default() -> None:
    rbac = RBACService()
    principal = _principal("owner")

    # An unknown permission must deny even for 'owner' (deny by default rule)
    with pytest.raises(AuthorizationError):
        rbac.require(principal, "some_unknown_permission_never_exists")


@pytest.mark.asyncio
async def test_research_service_delegates_to_central_rbac_gate() -> None:
    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()

    # Spy on rbac.require
    rbac = RBACService()
    patcher = patch.object(rbac, "require", side_effect=rbac.require)
    rbac_require_mock = patcher.start()

    # Set up campaign
    campaign = CampaignRecord(
        id=_CAMPAIGN,
        tenant_id=_TENANT,
        created_by_user_id=_ACTOR,
        name="Test",
        description=None,
        goal=None,
        target_segment=None,
        notes=None,
        status="ready",
    )
    camp_store.campaigns[_CAMPAIGN] = campaign

    contact1 = CampaignContactRecord(
        id=uuid.uuid4(),
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        contact_id=_CONTACT_1,
        status="selected",
    )
    camp_store.contacts[contact1.id] = contact1

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=rbac,
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
    )

    principal = _principal()
    await service.start_research_run(principal=principal, campaign_id=_CAMPAIGN, now=_NOW)

    # Assert that rbac.require was called with principal and permission 'campaign:run'
    rbac_require_mock.assert_called_with(principal, "campaign:run")
    patcher.stop()


@pytest.mark.asyncio
async def test_start_research_run_billing_denied() -> None:
    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=False)),  # Feature disabled
        queue=queue,
    )

    with pytest.raises(BillingAccessDenied):
        await service.start_research_run(principal=_principal(), campaign_id=_CAMPAIGN, now=_NOW)


@pytest.mark.asyncio
async def test_start_research_run_object_auth_denied() -> None:
    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()

    # Campaign belongs to OTHER tenant
    campaign = CampaignRecord(
        id=_CAMPAIGN,
        tenant_id=_OTHER_TENANT,
        created_by_user_id=_ACTOR,
        name="Other Campaign",
        description=None,
        goal=None,
        target_segment=None,
        notes=None,
        status="ready",
    )
    camp_store.campaigns[_CAMPAIGN] = campaign

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
    )

    with pytest.raises(AuthorizationError):
        await service.start_research_run(principal=_principal(), campaign_id=_CAMPAIGN, now=_NOW)


@pytest.mark.asyncio
async def test_start_research_run_idempotency_replay() -> None:
    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()
    idem = _IdempotencyGate(outcome=IdempotencyOutcome(IdempotencyState.REPLAY, status_code=201))

    # Campaign
    campaign = CampaignRecord(
        id=_CAMPAIGN,
        tenant_id=_TENANT,
        created_by_user_id=_ACTOR,
        name="Test",
        description=None,
        goal=None,
        target_segment=None,
        notes=None,
        status="ready",
    )
    camp_store.campaigns[_CAMPAIGN] = campaign

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
        idempotency=idem,
    )

    res = await service.start_research_run(
        principal=_principal(), campaign_id=_CAMPAIGN, idempotency_key="safe_key", now=_NOW
    )

    assert res.run is None
    assert res.idempotency_replay is True
    assert len(idem.begin_calls) == 1


# 4. Worker job handler tests
@pytest.mark.asyncio
async def test_worker_handler_verifies_tenant_context_and_executes() -> None:
    run_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    job = _FakeJob(
        tenant_id=_TENANT,
        payload={"research_run_id": str(run_id), "contact_id": str(contact_id)},
    )

    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()
    compliance = _FakeCompliance()
    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
        compliance=compliance,
        audit_record=record_audit,
    )

    # Mock DB connection which returns the correct tenant ID
    conn = _FakeAsyncConnection(current_tenant_val=str(_TENANT))

    # Add mock contacts to store
    store.contacts[contact_id] = _FakeContact(
        id=contact_id,
        tenant_id=_TENANT,
        email="cre_contact@example.com",
        company_name="CRE Corp",
        full_name="Alice Smith",
    )

    # Set up research run record in store
    run = ResearchRunRecord(
        id=run_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        created_by_user_id=_ACTOR,
        status="pending",
        queued_count=1,
        processed_count=0,
        failed_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    store.runs[run_id] = run

    # Patch ResearchRepository inside handle_research_job so we can run on memory fake
    with patch("app.repositories.research_repo.ResearchRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_run = AsyncMock(return_value=run)
        mock_repo.get_contact = AsyncMock(return_value=store.contacts[contact_id])
        mock_repo.update_run = AsyncMock(side_effect=store.update_run)
        mock_repo.increment_run_counts = AsyncMock(side_effect=store.increment_run_counts)
        mock_repo.create_artifact = AsyncMock(side_effect=store.create_artifact)

        await service.handle_research_job(job, conn)

        # Worker handler uses tenant-scoped connection
        # It must verify app.current_tenant_id matches
        assert any(
            "current_setting('app.current_tenant_id', true)" in str(q[0])
            for q in conn.executed_queries
        )

        # Mock research artifact creation succeeds
        assert len(store.artifacts) == 1
        artifact = list(store.artifacts.values())[0]
        assert artifact.research_run_id == run_id
        assert artifact.contact_id == contact_id
        assert artifact.findings["contact_email"] == "cre_contact@example.com"

        # Status transitions checked: pending -> running -> completed
        # Because we only have 1 queued count, the run immediately completes
        final_run = store.runs[run_id]
        assert final_run.processed_count == 1
        assert final_run.status == "completed"

        # Audits check
        # research.artifact_created and research.run_completed should be emitted
        event_types = [e["event_type"] for e in audit_events]
        assert "research.artifact_created" in event_types
        assert "research.run_completed" in event_types


@pytest.mark.asyncio
async def test_worker_handler_missing_tenant_context_fails_closed() -> None:
    job = _FakeJob(
        tenant_id=_TENANT,
        payload={"research_run_id": str(uuid.uuid4()), "contact_id": str(uuid.uuid4())},
    )
    service = ResearchService(
        research_store=_FakeResearchStore(),
        campaign_store=_FakeResearchCampaignStore(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=_FakeQueue(),
    )

    # Context is None -> verify it raises RuntimeError and does not execute handler logic
    conn = _FakeAsyncConnection(current_tenant_val=None)

    with pytest.raises(RuntimeError, match="Missing or mismatched tenant context"):
        await service.handle_research_job(job, conn)


@pytest.mark.asyncio
async def test_worker_handler_compliance_suppressed_contact_fails_artifact() -> None:
    run_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    job = _FakeJob(
        tenant_id=_TENANT,
        payload={"research_run_id": str(run_id), "contact_id": str(contact_id)},
    )

    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()
    compliance = _FakeCompliance()
    compliance.suppressed_emails.add("suppressed@example.com")
    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
        compliance=compliance,
        audit_record=record_audit,
    )

    conn = _FakeAsyncConnection(current_tenant_val=str(_TENANT))

    store.contacts[contact_id] = _FakeContact(
        id=contact_id,
        tenant_id=_TENANT,
        email="suppressed@example.com",
        company_name="Suppressed Corp",
        full_name="Suppressed Contact",
    )

    run = ResearchRunRecord(
        id=run_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        created_by_user_id=_ACTOR,
        status="pending",
        queued_count=1,
        processed_count=0,
        failed_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    store.runs[run_id] = run

    with patch("app.repositories.research_repo.ResearchRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_run = AsyncMock(return_value=run)
        mock_repo.get_contact = AsyncMock(return_value=store.contacts[contact_id])
        mock_repo.update_run = AsyncMock(side_effect=store.update_run)
        mock_repo.increment_run_counts = AsyncMock(side_effect=store.increment_run_counts)
        mock_repo.create_artifact = AsyncMock(side_effect=store.create_artifact)

        await service.handle_research_job(job, conn)

        # Assert no artifact is created
        assert len(store.artifacts) == 0

        # Assert the count registers as failed and run resolves to failed status
        final_run = store.runs[run_id]
        assert final_run.failed_count == 1
        assert final_run.status == "failed"

        event_types = [e["event_type"] for e in audit_events]
        assert "research.run_failed" in event_types


@pytest.mark.asyncio
async def test_worker_handler_mock_failure_requested() -> None:
    run_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    job = _FakeJob(
        tenant_id=_TENANT,
        payload={"research_run_id": str(run_id), "contact_id": str(contact_id)},
    )

    store = _FakeResearchStore()
    camp_store = _FakeResearchCampaignStore()
    queue = _FakeQueue()
    audit_events: list[dict[str, Any]] = []

    async def record_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    service = ResearchService(
        research_store=store,
        campaign_store=camp_store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=True)),
        queue=queue,
        audit_record=record_audit,
    )

    conn = _FakeAsyncConnection(current_tenant_val=str(_TENANT))

    # Name triggers the fail request
    store.contacts[contact_id] = _FakeContact(
        id=contact_id,
        tenant_id=_TENANT,
        email="contact@example.com",
        company_name="Fail Corp",
        full_name="MockFailContact",
    )

    run = ResearchRunRecord(
        id=run_id,
        tenant_id=_TENANT,
        campaign_id=_CAMPAIGN,
        created_by_user_id=_ACTOR,
        status="pending",
        queued_count=1,
        processed_count=0,
        failed_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    store.runs[run_id] = run

    with patch("app.repositories.research_repo.ResearchRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_run = AsyncMock(return_value=run)
        mock_repo.get_contact = AsyncMock(return_value=store.contacts[contact_id])
        mock_repo.update_run = AsyncMock(side_effect=store.update_run)
        mock_repo.increment_run_counts = AsyncMock(side_effect=store.increment_run_counts)
        mock_repo.create_artifact = AsyncMock(side_effect=store.create_artifact)

        await service.handle_research_job(job, conn)

        # Artifact creation skipped
        assert len(store.artifacts) == 0

        # Register as failure
        final_run = store.runs[run_id]
        assert final_run.failed_count == 1
        assert final_run.status == "failed"

        event_types = [e["event_type"] for e in audit_events]
        assert "research.run_failed" in event_types
