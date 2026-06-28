"""Safe mock/local billing, usage, and access-gate API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.repositories.usage_repo import UsageSnapshotRecord
from app.services.billing import BillingPlan, TenantSubscriptionRecord
from app.services.billing_api import AccessGateSnapshot, BillingStateTransitionResult


class BillingPlanDTO(BaseModel):
    key: str
    name: str
    features: dict[str, bool]
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: BillingPlan) -> BillingPlanDTO:
        return cls(key=record.key, name=record.name, features=record.features)


class BillingSubscriptionDTO(BaseModel):
    plan: BillingPlanDTO | None = None
    tenant_status: str
    grace_until: datetime | None = None
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: TenantSubscriptionRecord | None) -> BillingSubscriptionDTO:
        if record is None:
            return cls(plan=None, tenant_status="inactive", grace_until=None)
        return cls(
            plan=BillingPlanDTO.from_record(record.plan),
            tenant_status=record.tenant_status,
            grace_until=record.grace_until,
        )


class BillingSubscriptionResponse(BaseModel):
    subscription: BillingSubscriptionDTO
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: TenantSubscriptionRecord | None) -> BillingSubscriptionResponse:
        return cls(subscription=BillingSubscriptionDTO.from_record(record))


class BillingAccessDTO(BaseModel):
    is_active: bool
    can_send: bool
    can_run_agents: bool
    can_create_campaign: bool
    can_export: bool
    mock_only: bool = True

    @classmethod
    def from_snapshot(cls, snapshot: AccessGateSnapshot) -> BillingAccessDTO:
        return cls(
            is_active=snapshot.is_active,
            can_send=snapshot.can_send,
            can_run_agents=snapshot.can_run_agents,
            can_create_campaign=snapshot.can_create_campaign,
            can_export=snapshot.can_export,
            mock_only=snapshot.mock_only,
        )


class BillingAccessResponse(BaseModel):
    access: BillingAccessDTO
    mock_only: bool = True

    @classmethod
    def from_snapshot(cls, snapshot: AccessGateSnapshot) -> BillingAccessResponse:
        return cls(access=BillingAccessDTO.from_snapshot(snapshot))


class UsageSnapshotDTO(BaseModel):
    contacts_total: int
    contact_imports_total: int
    campaigns_total: int
    drafts_total: int
    outbound_mock_sent: int
    outbound_blocked: int
    send_gate_denied: int
    followups_mock_sent: int
    followups_skipped: int
    research_runs_total: int
    outcome_events_total: int
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: UsageSnapshotRecord) -> UsageSnapshotDTO:
        return cls(
            contacts_total=record.contacts_total,
            contact_imports_total=record.contact_imports_total,
            campaigns_total=record.campaigns_total,
            drafts_total=record.drafts_total,
            outbound_mock_sent=record.outbound_mock_sent,
            outbound_blocked=record.outbound_blocked,
            send_gate_denied=record.send_gate_denied,
            followups_mock_sent=record.followups_mock_sent,
            followups_skipped=record.followups_skipped,
            research_runs_total=record.research_runs_total,
            outcome_events_total=record.outcome_events_total,
        )


class UsageResponse(BaseModel):
    usage: UsageSnapshotDTO
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: UsageSnapshotRecord) -> UsageResponse:
        return cls(usage=UsageSnapshotDTO.from_record(record))


class BillingStateTransitionRequest(BaseModel):
    tenant_status: str
    grace_until: datetime | None = None


class StripeCheckoutSessionRequest(BaseModel):
    """Safe placeholder request for future test-mode checkout sessions."""

    model_config = ConfigDict(extra="forbid")


class StripePortalSessionRequest(BaseModel):
    """Safe placeholder request for future billing portal sessions."""

    model_config = ConfigDict(extra="forbid")


class StripeSessionResponse(BaseModel):
    """Safe future response shape for Stripe session endpoints."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    session_url: str | None = None
    mock_only: bool = True


class BillingStateTransitionResponse(BaseModel):
    subscription: BillingSubscriptionDTO
    idempotency_replay: bool = False
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: BillingStateTransitionResult) -> BillingStateTransitionResponse:
        return cls(
            subscription=BillingSubscriptionDTO.from_record(result.subscription),
            idempotency_replay=result.idempotency_replay,
            mock_only=result.mock_only,
        )
