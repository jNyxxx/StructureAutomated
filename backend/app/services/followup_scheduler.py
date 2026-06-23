"""Follow-up scheduler service for Phase 1 Slice P1-10."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.repositories.followup_repo import (
    FollowUpRepository,
    FollowUpRuleRecord,
    FollowUpScheduleRecord,
)
from app.services.authz import (
    CAN_RUN_CAMPAIGN,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)
from app.services.billing import BillingAccessDenied, BillingGateService
from app.services.queue import JobRecord, QueueService
from app.services.rate_limit import RateLimitPolicy, RateLimitService
from app.services.send_gate import SendGateService


class FollowUpStore(Protocol):
    async def create_followup_rule(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        delay_seconds: int,
    ) -> FollowUpRuleRecord: ...

    async def get_followup_rule_by_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> FollowUpRuleRecord | None: ...

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
    ) -> FollowUpScheduleRecord: ...

    async def get_followup_schedule(
        self, *, tenant_id: uuid.UUID, schedule_id: uuid.UUID
    ) -> FollowUpScheduleRecord | None: ...

    async def get_followup_schedule_by_original_message(
        self, *, tenant_id: uuid.UUID, original_outbound_message_id: uuid.UUID
    ) -> FollowUpScheduleRecord | None: ...

    async def update_followup_schedule_status(
        self,
        *,
        tenant_id: uuid.UUID,
        schedule_id: uuid.UUID,
        status: str,
    ) -> FollowUpScheduleRecord | None: ...


class CampaignStore(Protocol):
    async def get_campaign(self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Any | None: ...


class DraftStore(Protocol):
    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> Any | None: ...


class FollowUpSchedulerService:
    """Manages scheduling, outbox queueing, and mock execution of automated campaign follow-ups."""

    def __init__(
        self,
        *,
        followup_store: FollowUpStore,
        campaign_store: CampaignStore,
        draft_store: DraftStore,
        queue_service: QueueService,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
        billing: BillingGateService,
        rate_limiter: RateLimitService | None = None,
        rate_limit_policy: RateLimitPolicy | None = None,
        compliance: Any = None,
        audit_record: Any = None,
        followup_repo_factory: Callable[[Any], Any] = FollowUpRepository,
    ) -> None:
        self._followup_store = followup_store
        self._campaign_store = campaign_store
        self._draft_store = draft_store
        self._queue_service = queue_service
        self._rbac = rbac
        self._object_authz = object_authz
        self._billing = billing
        self._rate_limiter = rate_limiter
        self._rate_limit_policy = rate_limit_policy
        self._compliance = compliance
        self._audit_record = audit_record
        self._followup_repo_factory = followup_repo_factory

    async def create_followup_rule(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID,
        delay_seconds: int,
    ) -> FollowUpRuleRecord:
        """Create a new follow-up rule config for a campaign."""
        # 1. RBAC check
        self._rbac.require(principal, CAN_RUN_CAMPAIGN)

        # 2. Check campaign tenant isolation
        campaign = await self._campaign_store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        if campaign is None:
            raise AppError("CAMPAIGN_NOT_FOUND", "Campaign not found.", status_code=404)
        if campaign.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=campaign_id, tenant_id=campaign.tenant_id),
        )

        # 3. Validate delay_seconds
        if delay_seconds <= 0:
            raise AppError(
                "INVALID_DELAY", "Delay seconds must be greater than zero.", status_code=400
            )

        # 4. Check if rule already exists (unique per campaign)
        existing = await self._followup_store.get_followup_rule_by_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        if existing is not None:
            raise AppError(
                "DUPLICATE_RULE",
                "A follow-up rule already exists for this campaign.",
                status_code=409,
            )

        # 5. Create
        return await self._followup_store.create_followup_rule(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            delay_seconds=delay_seconds,
        )

    async def schedule_followup(
        self,
        principal: CurrentPrincipal,
        *,
        draft_id: uuid.UUID,
        outbound_message_id: uuid.UUID,
        now: datetime,
    ) -> FollowUpScheduleRecord | None:
        """Schedule a follow-up schedule and enqueue a delayed queue job."""
        # 1. Retrieve draft
        draft = await self._draft_store.get_draft(tenant_id=principal.tenant_id, draft_id=draft_id)
        if draft is None:
            raise AppError("DRAFT_NOT_FOUND", "Draft not found.", status_code=404)
        if draft.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=draft_id, tenant_id=draft.tenant_id),
        )

        # 2. Lookup rule for the campaign
        rule = await self._followup_store.get_followup_rule_by_campaign(
            tenant_id=principal.tenant_id, campaign_id=draft.campaign_id
        )
        if rule is None:
            return None

        # 3. Prevent duplicates
        existing = await self._followup_store.get_followup_schedule_by_original_message(
            tenant_id=principal.tenant_id, original_outbound_message_id=outbound_message_id
        )
        if existing is not None:
            raise AppError(
                "DUPLICATE_FOLLOWUP",
                "Follow-up already scheduled for this message.",
                status_code=409,
            )

        # 4. Create schedule
        run_after = now + timedelta(seconds=rule.delay_seconds)
        schedule = await self._followup_store.create_followup_schedule(
            tenant_id=principal.tenant_id,
            campaign_id=draft.campaign_id,
            contact_id=draft.contact_id,
            original_outbound_message_id=outbound_message_id,
            original_draft_id=draft_id,
            followup_rule_id=rule.id,
            status="scheduled",
            run_after=run_after,
            actor_user_id=principal.user_id,
            actor_role=principal.role,
        )

        # 5. Enqueue background queue job (runs at run_after)
        await self._queue_service.enqueue(
            tenant_id=principal.tenant_id,
            job_type="send_followup",
            payload={"followup_schedule_id": str(schedule.id)},
            now=run_after,
        )

        # 6. Update status to queued
        queued_schedule = await self._followup_store.update_followup_schedule_status(
            tenant_id=principal.tenant_id,
            schedule_id=schedule.id,
            status="queued",
        )

        # 7. Audit
        await self._audit(
            event_type="followup.scheduled",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="followup_schedule",
            object_id=schedule.id,
            details={
                "original_message_id": str(outbound_message_id),
                "run_after": run_after.isoformat(),
            },
        )

        return queued_schedule

    async def cancel_followup(
        self,
        principal: CurrentPrincipal,
        *,
        schedule_id: uuid.UUID,
    ) -> FollowUpScheduleRecord:
        """Cancel a pending/scheduled follow-up."""
        # 1. RBAC check
        self._rbac.require(principal, CAN_RUN_CAMPAIGN)

        # 2. Retrieve schedule
        schedule = await self._followup_store.get_followup_schedule(
            tenant_id=principal.tenant_id, schedule_id=schedule_id
        )
        if schedule is None:
            raise AppError("FOLLOWUP_SCHEDULE_NOT_FOUND", "Schedule not found.", status_code=404)
        if schedule.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=schedule_id, tenant_id=schedule.tenant_id),
        )

        # 3. Check status
        if schedule.status not in ("scheduled", "queued"):
            raise AppError(
                "INVALID_STATE",
                f"Cannot cancel follow-up schedule in status: {schedule.status}",
                status_code=400,
            )

        # 4. Cancel
        updated = await self._followup_store.update_followup_schedule_status(
            tenant_id=principal.tenant_id,
            schedule_id=schedule_id,
            status="canceled",
        )

        # 5. Audit
        await self._audit(
            event_type="followup.canceled",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="followup_schedule",
            object_id=schedule_id,
            details={},
        )

        if updated is None:
            raise AppError("UPDATE_FAILED", "Failed to cancel follow-up.", status_code=500)
        return updated

    async def process_job(self, job: JobRecord, conn: Any) -> None:
        """Durable background worker handler for 'send_followup' outbox jobs."""
        # 1. Extract payload
        schedule_id = uuid.UUID(job.payload["followup_schedule_id"])

        # 2. Instantiate repos tied to job's tenant connection
        followup_repo = self._followup_repo_factory(conn)

        schedule = await followup_repo.get_followup_schedule(
            tenant_id=job.tenant_id, schedule_id=schedule_id
        )
        if schedule is None:
            raise AppError("FOLLOWUP_SCHEDULE_NOT_FOUND", "Schedule not found.", status_code=404)

        # Tenant boundary check at repo level
        if schedule.tenant_id != job.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        # Idempotency / Duplicate Send prevention
        if schedule.status != "queued":
            # Already completed (mock_sent, skipped, canceled, etc.)
            return

        # 3. Reconstruct actor principal to pass gates
        principal = CurrentPrincipal(
            provider_user_id="worker",
            provider_session_ref="worker",
            user_id=schedule.actor_user_id,
            email="worker@system.local",
            tenant_id=schedule.tenant_id,
            role=schedule.actor_role,
            membership_version=1,
            mfa_verified=True,
        )

        # 4. Instantiate rest of repos and services tied to job connection
        from app.repositories.billing_repo import BillingRepository
        from app.repositories.compliance_repo import ComplianceRepository
        from app.repositories.draft_repo import DraftRepository
        from app.repositories.review_repo import ReviewRepository
        from app.repositories.safety_repo import SafetyRepository
        from app.repositories.sending_repo import SendingRepository
        from app.services.billing import BillingGateService
        from app.services.compliance import ComplianceGateService

        draft_repo = DraftRepository(conn)
        sending_repo = SendingRepository(conn)
        review_repo = ReviewRepository(conn)
        safety_repo = SafetyRepository(conn)
        billing_repo = BillingRepository(conn)
        compliance_repo = ComplianceRepository(conn)

        class ContactStoreImpl:
            def __init__(self, c: Any) -> None:
                self.conn = c

            async def get_contact(
                self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
            ) -> Any | None:
                from sqlalchemy import select

                from app.models.contact import Contact

                row = (
                    (
                        await self.conn.execute(
                            select(Contact).where(
                                Contact.tenant_id == tenant_id, Contact.id == contact_id
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
                return row

        contact_store = ContactStoreImpl(conn)
        billing_gate = BillingGateService(billing_repo)
        compliance_gate = ComplianceGateService(compliance_repo)

        send_gate_service = SendGateService(
            sending_store=sending_repo,
            draft_store=draft_repo,
            review_store=review_repo,
            safety_store=safety_repo,
            contact_store=contact_store,
            billing=billing_gate,
            rbac=self._rbac,
            object_authz=self._object_authz,
            compliance=compliance_gate,
            rate_limiter=self._rate_limiter,
            rate_limit_policy=self._rate_limit_policy,
            audit_record=self._audit_record,
        )

        now = datetime.now(schedule.run_after.tzinfo)

        # 5. Evaluate Gates again before sending follow-up
        try:
            await send_gate_service.evaluate_gate(
                principal=principal,
                draft_id=schedule.original_draft_id,
                now=now,
                is_followup=True,
            )
        except (AppError, BillingAccessDenied) as e:
            # Denied/skipped by policy gates
            await followup_repo.update_followup_schedule_status(
                tenant_id=schedule.tenant_id,
                schedule_id=schedule.id,
                status="skipped",
            )
            await self._audit(
                event_type="followup.skipped",
                tenant_id=schedule.tenant_id,
                actor_user_id=schedule.actor_user_id,
                object_type="followup_schedule",
                object_id=schedule.id,
                details={"reason": getattr(e, "code", type(e).__name__)},
            )
            return
        except Exception:
            # Mark schedule as failed if some technical issue arises
            await followup_repo.update_followup_schedule_status(
                tenant_id=schedule.tenant_id,
                schedule_id=schedule.id,
                status="failed",
            )
            raise

        # 6. Success: Transition to mock_sent
        await followup_repo.update_followup_schedule_status(
            tenant_id=schedule.tenant_id,
            schedule_id=schedule.id,
            status="mock_sent",
        )

        # 7. Audit
        await self._audit(
            event_type="followup.mock_sent",
            tenant_id=schedule.tenant_id,
            actor_user_id=schedule.actor_user_id,
            object_type="followup_schedule",
            object_id=schedule.id,
            details={"original_draft_id": str(schedule.original_draft_id)},
        )

    async def _audit(
        self,
        *,
        event_type: str,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        object_type: str,
        object_id: uuid.UUID,
        details: dict[str, Any],
    ) -> None:
        if self._audit_record is not None:
            if callable(self._audit_record):
                await self._audit_record(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    object_type=object_type,
                    object_id=object_id,
                    details=details,
                )
            else:
                await self._audit_record.record(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    object_type=object_type,
                    object_id=object_id,
                    details=details,
                )
