"""Campaign creation and contact selection service for Phase 1 Slice P1-02.

No AI research, RAG, draft generation, review, sending, follow-ups, dashboards,
webhooks, or provider integrations are implemented here.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import CAN_CREATE_CAMPAIGN as AUTHZ_CAN_CREATE_CAMPAIGN
from app.services.authz import ObjectAuthorizationService, RBACService, TenantOwnedObject
from app.services.billing import CAN_CREATE_CAMPAIGN as BILLING_CAN_CREATE_CAMPAIGN
from app.services.billing import BillingGateService
from app.services.idempotency import IdempotencyOutcome, IdempotencyState


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PAUSED = "paused"
    ARCHIVED = "archived"


class CampaignContactStatus(StrEnum):
    SELECTED = "selected"
    EXCLUDED = "excluded"
    QUEUED_FOR_RESEARCH = "queued_for_research"


@dataclass(frozen=True)
class CampaignRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    name: str
    description: str | None
    goal: str | None
    target_segment: str | None
    notes: str | None
    status: str


@dataclass(frozen=True)
class CampaignContactRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    status: str


@dataclass(frozen=True)
class CampaignCreateResult:
    campaign: CampaignRecord | None
    idempotency_replay: bool = False


@dataclass(frozen=True)
class CampaignUpdateResult:
    campaign: CampaignRecord | None
    idempotency_replay: bool = False


@dataclass(frozen=True)
class CampaignContactSelectionResult:
    campaign_contact: CampaignContactRecord | None
    idempotency_replay: bool = False


class IdempotencyGate(Protocol):
    async def begin(
        self,
        *,
        key: str,
        request_payload: Any,
        now: datetime,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> IdempotencyOutcome:
        """Begin an idempotent operation."""

    async def complete(
        self,
        *,
        key: str,
        response_payload: Any,
        status_code: int,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        """Complete an idempotent operation."""


class CampaignStore(Protocol):
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
        """Create a campaign."""

    async def get_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> CampaignRecord | None:
        """Return a campaign by tenant/id."""

    async def list_campaigns(self, *, tenant_id: uuid.UUID) -> list[CampaignRecord]:
        """List campaigns for a tenant."""

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
        """Update basic campaign metadata/status."""

    async def get_contact_object(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> TenantOwnedObject | None:
        """Return a tenant-owned contact object for authorization."""

    async def get_campaign_contact(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID, contact_id: uuid.UUID
    ) -> CampaignContactRecord | None:
        """Return campaign-contact row, if present."""

    async def attach_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord:
        """Attach or re-select a contact for a campaign."""

    async def set_campaign_contact_status(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord | None:
        """Update campaign-contact status."""

    async def list_campaign_contacts(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> list[CampaignContactRecord]:
        """List selected/excluded contacts for a campaign."""


AuditRecorder = Callable[..., Awaitable[None]]


def _clean_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise AppError("INVALID_CAMPAIGN", f"{field} is required.", status_code=400)
    return cleaned


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _validate_campaign_status(status: str) -> None:
    if status not in {item.value for item in CampaignStatus}:
        raise AppError("INVALID_CAMPAIGN_STATUS", "Invalid campaign status.", status_code=400)


def _validate_campaign_contact_status(status: str) -> None:
    if status not in {item.value for item in CampaignContactStatus}:
        raise AppError(
            "INVALID_CAMPAIGN_CONTACT_STATUS",
            "Invalid campaign contact status.",
            status_code=400,
        )


def _obj(record: CampaignRecord | None) -> TenantOwnedObject | None:
    if record is None:
        return None
    return TenantOwnedObject(id=record.id, tenant_id=record.tenant_id)


class CampaignService:
    """Campaign foundation behind Phase 0 central gates."""

    def __init__(
        self,
        *,
        store: CampaignStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
        billing: BillingGateService,
        idempotency: IdempotencyGate | None = None,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._store = store
        self._rbac = rbac
        self._object_authz = object_authz
        self._billing = billing
        self._idempotency = idempotency
        self._audit_record = audit_record

    async def create_campaign(
        self,
        *,
        principal: CurrentPrincipal,
        name: str,
        description: str | None,
        goal: str | None,
        target_segment: str | None,
        notes: str | None,
        idempotency_key: str | None,
        now: datetime,
    ) -> CampaignCreateResult:
        self._rbac.require(principal, AUTHZ_CAN_CREATE_CAMPAIGN)
        await self._billing.require_feature(
            principal.tenant_id, BILLING_CAN_CREATE_CAMPAIGN, now=now
        )
        cleaned_name = _clean_required(name, field="name")
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "name": cleaned_name,
            "description": _clean_optional(description),
            "goal": _clean_optional(goal),
            "target_segment": _clean_optional(target_segment),
            "notes": _clean_optional(notes),
        }
        if self._idempotency is not None and idempotency_key is not None:
            outcome = await self._idempotency.begin(
                key=idempotency_key,
                request_payload=request_payload,
                now=now,
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
            if outcome.state is IdempotencyState.REPLAY:
                return CampaignCreateResult(campaign=None, idempotency_replay=True)
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "CAMPAIGN_CREATE_IN_PROGRESS",
                    "Campaign creation is already in progress.",
                    status_code=409,
                )

        campaign = await self._store.create_campaign(
            tenant_id=principal.tenant_id,
            created_by_user_id=principal.user_id,
            name=cleaned_name,
            description=request_payload["description"],
            goal=request_payload["goal"],
            target_segment=request_payload["target_segment"],
            notes=request_payload["notes"],
            status=CampaignStatus.DRAFT.value,
        )
        await self._audit(
            event_type="campaign.created",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_id=campaign.id,
            details={"status": campaign.status},
        )
        if self._idempotency is not None and idempotency_key is not None:
            await self._idempotency.complete(
                key=idempotency_key,
                response_payload={"campaign_id": str(campaign.id)},
                status_code=201,
                tenant_id=principal.tenant_id,
            )
        return CampaignCreateResult(campaign=campaign)

    async def get_campaign(
        self, *, principal: CurrentPrincipal, campaign_id: uuid.UUID
    ) -> CampaignRecord:
        campaign = await self._store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(campaign))
        if campaign is None:
            raise AppError("CAMPAIGN_NOT_FOUND", "Campaign not found.", status_code=404)
        return campaign

    async def list_campaigns(self, *, principal: CurrentPrincipal) -> list[CampaignRecord]:
        self._rbac.require(principal, AUTHZ_CAN_CREATE_CAMPAIGN)
        return await self._store.list_campaigns(tenant_id=principal.tenant_id)

    async def update_campaign_idempotent(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        goal: str | None = None,
        target_segment: str | None = None,
        notes: str | None = None,
        status: str | None = None,
        idempotency_key: str | None,
        now: datetime | None = None,
    ) -> CampaignUpdateResult:
        now = now or datetime.now(UTC)
        await self._billing.require_feature(
            principal.tenant_id, BILLING_CAN_CREATE_CAMPAIGN, now=now
        )
        if status is not None:
            _validate_campaign_status(status)
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "campaign_id": str(campaign_id),
            "name": _clean_required(name, field="name") if name is not None else None,
            "description": _clean_optional(description),
            "goal": _clean_optional(goal),
            "target_segment": _clean_optional(target_segment),
            "notes": _clean_optional(notes),
            "status": status,
        }
        if self._idempotency is not None and idempotency_key is not None:
            outcome = await self._idempotency.begin(
                key=idempotency_key,
                request_payload=request_payload,
                now=now,
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
            if outcome.state is IdempotencyState.REPLAY:
                return CampaignUpdateResult(campaign=None, idempotency_replay=True)
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "CAMPAIGN_UPDATE_IN_PROGRESS",
                    "Campaign update is already in progress.",
                    status_code=409,
                )
        updated = await self.update_campaign(
            principal=principal,
            campaign_id=campaign_id,
            name=request_payload["name"],
            description=request_payload["description"],
            goal=request_payload["goal"],
            target_segment=request_payload["target_segment"],
            notes=request_payload["notes"],
            status=status,
        )
        if self._idempotency is not None and idempotency_key is not None:
            await self._idempotency.complete(
                key=idempotency_key,
                response_payload={"campaign_id": str(updated.id)},
                status_code=200,
                tenant_id=principal.tenant_id,
            )
        return CampaignUpdateResult(campaign=updated)

    async def update_campaign(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        goal: str | None = None,
        target_segment: str | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> CampaignRecord:
        campaign = await self._store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=_obj(campaign),
            action=AUTHZ_CAN_CREATE_CAMPAIGN,
            rbac=self._rbac,
        )
        if status is not None:
            _validate_campaign_status(status)
        updated = await self._store.update_campaign(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            name=_clean_required(name, field="name") if name is not None else None,
            description=_clean_optional(description),
            goal=_clean_optional(goal),
            target_segment=_clean_optional(target_segment),
            notes=_clean_optional(notes),
            status=status,
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(updated))
        if updated is None:
            raise AppError("CAMPAIGN_NOT_FOUND", "Campaign not found.", status_code=404)
        await self._audit(
            event_type="campaign.updated",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_id=updated.id,
            details={"status": updated.status},
        )
        return updated

    async def attach_contact_idempotent(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str = CampaignContactStatus.SELECTED.value,
        idempotency_key: str | None,
        now: datetime | None = None,
    ) -> CampaignContactSelectionResult:
        now = now or datetime.now(UTC)
        await self._billing.require_feature(
            principal.tenant_id, BILLING_CAN_CREATE_CAMPAIGN, now=now
        )
        _validate_campaign_contact_status(status)
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "campaign_id": str(campaign_id),
            "contact_id": str(contact_id),
            "status": status,
        }
        if self._idempotency is not None and idempotency_key is not None:
            outcome = await self._idempotency.begin(
                key=idempotency_key,
                request_payload=request_payload,
                now=now,
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
            if outcome.state is IdempotencyState.REPLAY:
                return CampaignContactSelectionResult(
                    campaign_contact=None, idempotency_replay=True
                )
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "CAMPAIGN_CONTACT_SELECTION_IN_PROGRESS",
                    "Campaign contact selection is already in progress.",
                    status_code=409,
                )
        row = await self.attach_contact(
            principal=principal,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=status,
        )
        if self._idempotency is not None and idempotency_key is not None:
            await self._idempotency.complete(
                key=idempotency_key,
                response_payload={"campaign_contact_id": str(row.id)},
                status_code=201,
                tenant_id=principal.tenant_id,
            )
        return CampaignContactSelectionResult(campaign_contact=row)

    async def attach_contact(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str = CampaignContactStatus.SELECTED.value,
    ) -> CampaignContactRecord:
        _validate_campaign_contact_status(status)
        campaign = await self._store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=_obj(campaign),
            action=AUTHZ_CAN_CREATE_CAMPAIGN,
            rbac=self._rbac,
        )
        contact = await self._store.get_contact_object(
            tenant_id=principal.tenant_id,
            contact_id=contact_id,
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=contact)
        existing = await self._store.get_campaign_contact(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
        )
        if existing is None:
            row = await self._store.attach_contact(
                tenant_id=principal.tenant_id,
                campaign_id=campaign_id,
                contact_id=contact_id,
                status=status,
            )
        elif existing.status == status:
            row = existing
        else:
            updated = await self._store.set_campaign_contact_status(
                tenant_id=principal.tenant_id,
                campaign_id=campaign_id,
                contact_id=contact_id,
                status=status,
            )
            if updated is None:
                raise AppError(
                    "CAMPAIGN_CONTACT_NOT_FOUND",
                    "Campaign contact not found.",
                    status_code=404,
                )
            row = updated
        await self._audit(
            event_type="campaign.contact_selected",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_id=campaign_id,
            details={"status": row.status},
        )
        return row

    async def remove_contact(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
    ) -> CampaignContactRecord:
        campaign = await self._store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=_obj(campaign),
            action=AUTHZ_CAN_CREATE_CAMPAIGN,
            rbac=self._rbac,
        )
        contact = await self._store.get_contact_object(
            tenant_id=principal.tenant_id,
            contact_id=contact_id,
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=contact)
        updated = await self._store.set_campaign_contact_status(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            status=CampaignContactStatus.EXCLUDED.value,
        )
        if updated is None:
            raise AppError(
                "CAMPAIGN_CONTACT_NOT_FOUND", "Campaign contact not found.", status_code=404
            )
        await self._audit(
            event_type="campaign.contact_removed",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_id=campaign_id,
            details={"status": updated.status},
        )
        return updated

    async def list_campaign_contacts(
        self, *, principal: CurrentPrincipal, campaign_id: uuid.UUID
    ) -> list[CampaignContactRecord]:
        campaign = await self._store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(campaign))
        return await self._store.list_campaign_contacts(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )

    async def _audit(
        self,
        *,
        event_type: str,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        object_id: uuid.UUID,
        details: dict[str, Any],
    ) -> None:
        if self._audit_record is None:
            return
        await self._audit_record(
            event_type=event_type,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            object_type="campaign",
            object_id=object_id,
            details=details,
        )
