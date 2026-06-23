"""Campaign creation and contact selection tests (Phase 1 P1-02)."""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.models import Campaign, CampaignContact
from app.services.authz import ObjectAuthorizationService, RBACService, TenantOwnedObject
from app.services.billing import (
    CAN_CREATE_CAMPAIGN,
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)
from app.services.campaign import (
    CampaignContactRecord,
    CampaignCreateResult,
    CampaignRecord,
    CampaignService,
)
from app.services.idempotency import IdempotencyOutcome, IdempotencyState

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CAMPAIGN = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_OTHER_CONTACT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_PLAN_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_NOW = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)


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
                features={CAN_CREATE_CAMPAIGN: allowed},
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
        raise AssertionError("not used by campaign tests")


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


class _Store:
    def __init__(self) -> None:
        self.campaigns: dict[uuid.UUID, CampaignRecord] = {}
        self.contacts: dict[uuid.UUID, TenantOwnedObject] = {
            _CONTACT: TenantOwnedObject(id=_CONTACT, tenant_id=_TENANT),
            _OTHER_CONTACT: TenantOwnedObject(id=_OTHER_CONTACT, tenant_id=_OTHER_TENANT),
        }
        self.campaign_contacts: dict[tuple[uuid.UUID, uuid.UUID], CampaignContactRecord] = {}
        self._next = 1

    def _id(self) -> uuid.UUID:
        value = uuid.UUID(f"00000000-0000-0000-0000-{self._next:012d}")
        self._next += 1
        return value

    async def create_campaign(
        self,
        *,
        tenant_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        name: str,
        description: str | None,
        goal: str | None,
        target_segment: str | None,
        notes: str | None,
        status: str,
    ) -> CampaignRecord:
        campaign = CampaignRecord(
            id=self._id(),
            tenant_id=tenant_id,
            created_by_user_id=created_by_user_id,
            name=name,
            description=description,
            goal=goal,
            target_segment=target_segment,
            notes=notes,
            status=status,
        )
        self.campaigns[campaign.id] = campaign
        return campaign

    async def get_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> CampaignRecord | None:
        campaign = self.campaigns.get(campaign_id)
        if campaign is None or campaign.tenant_id != tenant_id:
            return None
        return campaign

    async def list_campaigns(self, *, tenant_id: uuid.UUID) -> list[CampaignRecord]:
        return [campaign for campaign in self.campaigns.values() if campaign.tenant_id == tenant_id]

    async def update_campaign(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        name: str | None,
        description: str | None,
        goal: str | None,
        target_segment: str | None,
        notes: str | None,
        status: str | None,
    ) -> CampaignRecord | None:
        campaign = await self.get_campaign(tenant_id=tenant_id, campaign_id=campaign_id)
        if campaign is None:
            return None
        updated = CampaignRecord(
            id=campaign.id,
            tenant_id=campaign.tenant_id,
            created_by_user_id=campaign.created_by_user_id,
            name=name if name is not None else campaign.name,
            description=description if description is not None else campaign.description,
            goal=goal if goal is not None else campaign.goal,
            target_segment=(
                target_segment if target_segment is not None else campaign.target_segment
            ),
            notes=notes if notes is not None else campaign.notes,
            status=status if status is not None else campaign.status,
        )
        self.campaigns[updated.id] = updated
        return updated

    async def get_contact_object(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> TenantOwnedObject | None:
        contact = self.contacts.get(contact_id)
        if contact is None or contact.tenant_id != tenant_id:
            return None
        return contact

    async def get_campaign_contact(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID, contact_id: uuid.UUID
    ) -> CampaignContactRecord | None:
        row = self.campaign_contacts.get((campaign_id, contact_id))
        if row is None or row.tenant_id != tenant_id:
            return None
        return row

    async def attach_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord:
        row = CampaignContactRecord(
            id=self._id(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=status,
        )
        self.campaign_contacts[(campaign_id, contact_id)] = row
        return row

    async def set_campaign_contact_status(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord | None:
        row = await self.get_campaign_contact(
            tenant_id=tenant_id, campaign_id=campaign_id, contact_id=contact_id
        )
        if row is None:
            return None
        updated = CampaignContactRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            campaign_id=row.campaign_id,
            contact_id=row.contact_id,
            status=status,
        )
        self.campaign_contacts[(campaign_id, contact_id)] = updated
        return updated

    async def list_campaign_contacts(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> list[CampaignContactRecord]:
        return [
            row
            for row in self.campaign_contacts.values()
            if row.tenant_id == tenant_id and row.campaign_id == campaign_id
        ]


def _service(
    store: _Store,
    *,
    billing_allowed: bool = True,
    idempotency: _IdempotencyGate | None = None,
    audits: list[dict[str, Any]] | None = None,
) -> CampaignService:
    async def audit_record(**kwargs: Any) -> None:
        if audits is not None:
            audits.append(kwargs)

    return CampaignService(
        store=store,
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
        billing=BillingGateService(_BillingStore(allowed=billing_allowed)),
        idempotency=idempotency,
        audit_record=audit_record,
    )


async def _create(
    service: CampaignService,
    *,
    principal: CurrentPrincipal | None = None,
    idempotency_key: str | None = "campaign-key-1",
) -> CampaignCreateResult:
    return await service.create_campaign(
        principal=principal or _principal(),
        name="Q3 CRE Owners",
        description="Local demo campaign",
        goal="Book discovery calls",
        target_segment="Commercial real estate owners",
        notes="Use local/mock data only",
        idempotency_key=idempotency_key,
        now=_NOW,
    )


def test_campaign_models_are_tenant_owned_and_constrained() -> None:
    for model in (Campaign, CampaignContact):
        assert model.__table__.c.tenant_id.nullable is False

    campaign_table: Any = Campaign.__table__
    campaign_contact_table: Any = CampaignContact.__table__
    campaign_checks = [
        str(c.sqltext) for c in campaign_table.constraints if isinstance(c, CheckConstraint)
    ]
    contact_checks = [
        str(c.sqltext) for c in campaign_contact_table.constraints if isinstance(c, CheckConstraint)
    ]
    contact_uniques = [
        frozenset(col.name for col in c.columns)
        for c in campaign_contact_table.constraints
        if isinstance(c, UniqueConstraint)
    ]

    assert any("draft" in check and "archived" in check for check in campaign_checks)
    assert any("selected" in check and "queued_for_research" in check for check in contact_checks)
    assert frozenset({"campaign_id", "contact_id"}) in contact_uniques


async def test_campaign_create_list_read_update_idempotency_and_audit() -> None:
    store = _Store()
    idempotency = _IdempotencyGate()
    audits: list[dict[str, Any]] = []
    service = _service(store, idempotency=idempotency, audits=audits)

    result = await _create(service)
    assert result.campaign is not None
    campaign = result.campaign
    listed = await service.list_campaigns(principal=_principal())
    read = await service.get_campaign(principal=_principal(), campaign_id=campaign.id)
    updated = await service.update_campaign(
        principal=_principal(), campaign_id=campaign.id, name="Updated", status="ready"
    )

    assert [item.id for item in listed] == [campaign.id]
    assert read.id == campaign.id
    assert updated.name == "Updated"
    assert updated.status == "ready"
    assert idempotency.begin_calls[0]["tenant_id"] == _TENANT
    assert idempotency.complete_calls[0]["status_code"] == 201
    assert [audit["event_type"] for audit in audits] == ["campaign.created", "campaign.updated"]
    assert "Q3 CRE Owners" not in str(audits)


async def test_campaign_contact_attach_remove_and_duplicate_selection() -> None:
    store = _Store()
    service = _service(store)
    created = await _create(service, idempotency_key=None)
    assert created.campaign is not None

    first = await service.attach_contact(
        principal=_principal(), campaign_id=created.campaign.id, contact_id=_CONTACT
    )
    duplicate = await service.attach_contact(
        principal=_principal(), campaign_id=created.campaign.id, contact_id=_CONTACT
    )
    listed = await service.list_campaign_contacts(
        principal=_principal(), campaign_id=created.campaign.id
    )
    removed = await service.remove_contact(
        principal=_principal(), campaign_id=created.campaign.id, contact_id=_CONTACT
    )

    assert first.id == duplicate.id
    assert len(listed) == 1
    assert removed.status == "excluded"
    assert len(store.campaign_contacts) == 1


async def test_selected_contact_must_belong_to_same_tenant() -> None:
    store = _Store()
    service = _service(store)
    created = await _create(service, idempotency_key=None)
    assert created.campaign is not None

    with pytest.raises(AppError) as exc:
        await service.attach_contact(
            principal=_principal(), campaign_id=created.campaign.id, contact_id=_OTHER_CONTACT
        )

    assert exc.value.code == "OBJECT_ACCESS_DENIED"
    assert store.campaign_contacts == {}


async def test_tenant_isolation_prevents_cross_tenant_campaign_access() -> None:
    store = _Store()
    service = _service(store)
    created = await _create(service, idempotency_key=None)
    assert created.campaign is not None

    with pytest.raises(AppError) as exc:
        await service.get_campaign(
            principal=_principal(tenant_id=_OTHER_TENANT), campaign_id=created.campaign.id
        )

    assert exc.value.code == "OBJECT_ACCESS_DENIED"


async def test_rbac_denied_case_blocks_campaign_creation_before_storage() -> None:
    store = _Store()
    service = _service(store)

    with pytest.raises(AppError) as exc:
        await _create(service, principal=_principal("viewer"))

    assert exc.value.code == "FORBIDDEN"
    assert store.campaigns == {}


async def test_billing_gate_denied_case_blocks_campaign_creation_before_storage() -> None:
    store = _Store()
    service = _service(store, billing_allowed=False)

    with pytest.raises(AppError) as exc:
        await _create(service)

    assert exc.value.code == "BILLING_FEATURE_DENIED"
    assert store.campaigns == {}


async def test_object_authorization_denied_case_for_missing_campaign_update() -> None:
    service = _service(_Store())

    with pytest.raises(AppError) as exc:
        await service.update_campaign(
            principal=_principal(), campaign_id=_CAMPAIGN, name="Missing campaign"
        )

    assert exc.value.code == "OBJECT_ACCESS_DENIED"


async def test_idempotency_replay_does_not_create_another_campaign() -> None:
    store = _Store()
    service = _service(
        store,
        idempotency=_IdempotencyGate(IdempotencyOutcome(IdempotencyState.REPLAY, 201, "hash")),
    )

    result = await _create(service)

    assert result.idempotency_replay is True
    assert result.campaign is None
    assert store.campaigns == {}


async def test_audit_events_for_contact_selected_and_removed_are_minimized() -> None:
    store = _Store()
    audits: list[dict[str, Any]] = []
    service = _service(store, audits=audits)
    created = await _create(service, idempotency_key=None)
    assert created.campaign is not None

    await service.attach_contact(
        principal=_principal(), campaign_id=created.campaign.id, contact_id=_CONTACT
    )
    await service.remove_contact(
        principal=_principal(), campaign_id=created.campaign.id, contact_id=_CONTACT
    )

    assert [audit["event_type"] for audit in audits] == [
        "campaign.created",
        "campaign.contact_selected",
        "campaign.contact_removed",
    ]
    rendered = str(audits).lower()
    assert "q3 cre owners" not in rendered
    assert "token" not in rendered
    assert "secret" not in rendered


def test_campaign_migration_shape_rls_and_no_later_phase1_workflows() -> None:
    src = (
        Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0012_campaigns.py"
    ).read_text(encoding="utf-8")

    assert "campaigns" in src
    assert "campaign_contacts" in src
    assert "tenant_id" in src
    assert "created_by_user_id" in src
    assert "target_segment" in src
    assert "draft" in src and "ready" in src and "paused" in src and "archived" in src
    assert "selected" in src and "excluded" in src and "queued_for_research" in src
    assert 'apply_forced_rls("campaigns")' in src
    assert 'apply_forced_rls("campaign_contacts")' in src
    lowered = src.lower()
    for forbidden in ("stripe", "twilio", "webhook", "live scraping", "draft generation", "rag"):
        assert forbidden not in lowered
