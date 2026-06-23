"""Research service for Phase 1 Slice P1-03."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import text

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import ObjectAuthorizationService, RBACService, TenantOwnedObject
from app.services.billing import CAN_RUN_AGENTS as BILLING_CAN_RUN_AGENTS
from app.services.billing import BillingGateService
from app.services.campaign import CampaignContactRecord, CampaignRecord
from app.services.idempotency import IdempotencyOutcome, IdempotencyState


@dataclass(frozen=True)
class ResearchRunRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    status: str
    queued_count: int
    processed_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ResearchArtifactRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    research_run_id: uuid.UUID
    contact_id: uuid.UUID
    findings: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class ResearchRunCreateResult:
    run: ResearchRunRecord | None
    idempotency_replay: bool = False


class ResearchCampaignStore(Protocol):
    async def get_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> CampaignRecord | None:
        """Return campaign details."""

    async def list_campaign_contacts(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> list[CampaignContactRecord]:
        """Return campaign selected contacts."""

    async def set_campaign_contact_status(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord | None:
        """Update campaign contact status."""


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


class QueueGate(Protocol):
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
        """Enqueue job."""


class ComplianceGate(Protocol):
    async def is_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> bool:
        """Check if suppressed."""


class ResearchStore(Protocol):
    async def create_run(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None,
        status: str,
        queued_count: int,
    ) -> ResearchRunRecord:
        """Create research run."""

    async def get_run(self, *, tenant_id: uuid.UUID, run_id: uuid.UUID) -> ResearchRunRecord | None:
        """Get research run."""

    async def update_run(
        self,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        status: str | None = None,
        processed_count: int | None = None,
        failed_count: int | None = None,
    ) -> ResearchRunRecord | None:
        """Update research run."""

    async def increment_run_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        processed: int = 0,
        failed: int = 0,
    ) -> ResearchRunRecord | None:
        """Atomically increment counters."""

    async def create_artifact(
        self,
        *,
        tenant_id: uuid.UUID,
        research_run_id: uuid.UUID,
        contact_id: uuid.UUID,
        findings: dict[str, Any],
    ) -> ResearchArtifactRecord:
        """Create research artifact."""

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any:
        """Get contact."""


AuditRecorder = Any


def _obj(record: CampaignRecord | None) -> TenantOwnedObject | None:
    if record is None:
        return None
    return TenantOwnedObject(id=record.id, tenant_id=record.tenant_id)


class ResearchService:
    """Research run and mock artifact execution service."""

    def __init__(
        self,
        *,
        research_store: ResearchStore,
        campaign_store: ResearchCampaignStore,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
        billing: BillingGateService,
        queue: QueueGate,
        compliance: ComplianceGate | None = None,
        idempotency: IdempotencyGate | None = None,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._research_store = research_store
        self._campaign_store = campaign_store
        self._rbac = rbac
        self._object_authz = object_authz
        self._billing = billing
        self._queue = queue
        self._compliance = compliance
        self._idempotency = idempotency
        self._audit_record = audit_record

    async def start_research_run(
        self,
        *,
        principal: CurrentPrincipal,
        campaign_id: uuid.UUID,
        idempotency_key: str | None = None,
        now: datetime,
    ) -> ResearchRunCreateResult:
        # 1. RBAC check
        self._rbac.require(principal, "campaign:run")

        # 2. Billing check
        await self._billing.require_feature(principal.tenant_id, BILLING_CAN_RUN_AGENTS, now=now)

        # 3. Fetch Campaign & Object Auth check
        campaign = await self._campaign_store.get_campaign(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        self._object_authz.require_tenant_owner(principal=principal, obj=_obj(campaign))
        if campaign is None:
            raise AppError("CAMPAIGN_NOT_FOUND", "Campaign not found.", status_code=404)

        # 4. Idempotency begin
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "campaign_id": str(campaign_id),
        }
        if self._idempotency is not None and idempotency_key is not None:
            outcome = await self._idempotency.begin(
                key=idempotency_key,
                request_payload=request_payload,
                now=now,
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
            if outcome.is_replay:
                return ResearchRunCreateResult(run=None, idempotency_replay=True)
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "RESEARCH_RUN_CREATE_IN_PROGRESS",
                    "Research run creation is already in progress.",
                    status_code=409,
                )

        # 5. Fetch Campaign Contacts
        all_contacts = await self._campaign_store.list_campaign_contacts(
            tenant_id=principal.tenant_id, campaign_id=campaign_id
        )
        selected_contacts = [
            c for c in all_contacts if c.status in ("selected", "queued_for_research")
        ]

        if not selected_contacts:
            raise AppError(
                "NO_SELECTED_CONTACTS",
                "No selected campaign contacts to research.",
                status_code=400,
            )

        # 6. Create ResearchRun
        run = await self._research_store.create_run(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            created_by_user_id=principal.user_id,
            status="pending",
            queued_count=len(selected_contacts),
        )

        # 7. Queue Jobs & Update status
        for contact in selected_contacts:
            # Deterministic job idempotency key
            job_key = f"research_job:{run.id}:{contact.contact_id}"
            await self._queue.enqueue(
                tenant_id=principal.tenant_id,
                job_type="research",
                payload={
                    "research_run_id": str(run.id),
                    "campaign_contact_id": str(contact.id),
                    "contact_id": str(contact.contact_id),
                },
                now=now,
                idempotency_key=job_key,
            )
            await self._campaign_store.set_campaign_contact_status(
                tenant_id=principal.tenant_id,
                campaign_id=campaign_id,
                contact_id=contact.contact_id,
                status="queued_for_research",
            )

        # 8. Audit event
        await self._audit(
            event_type="research.run_started",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="research_run",
            object_id=run.id,
            details={"campaign_id": str(campaign_id), "queued_count": len(selected_contacts)},
        )

        # 9. Idempotency complete
        if self._idempotency is not None and idempotency_key is not None:
            await self._idempotency.complete(
                key=idempotency_key,
                response_payload={"research_run_id": str(run.id)},
                status_code=201,
                tenant_id=principal.tenant_id,
            )

        return ResearchRunCreateResult(run=run)

    async def handle_research_job(self, job: Any, conn: Any) -> None:
        # 1. Tenant Context verification (Fail-closed check)
        result = await conn.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        current_tenant = result.scalar()
        if not current_tenant or uuid.UUID(current_tenant) != job.tenant_id:
            raise RuntimeError("Missing or mismatched tenant context")

        # 2. Extract payload variables
        run_id = uuid.UUID(job.payload["research_run_id"])
        contact_id = uuid.UUID(job.payload["contact_id"])

        # 3. Instantiate repository pre-bound to current tenant transaction
        from app.repositories.research_repo import ResearchRepository

        repo = ResearchRepository(conn)

        run = await repo.get_run(tenant_id=job.tenant_id, run_id=run_id)
        if run is None:
            raise AppError("RESEARCH_RUN_NOT_FOUND", "Research run not found.", status_code=404)

        # Transition run to 'running' if it is 'pending'
        if run.status == "pending":
            run = await repo.update_run(tenant_id=job.tenant_id, run_id=run_id, status="running")

        # 4. Load contact
        contact = await repo.get_contact(tenant_id=job.tenant_id, contact_id=contact_id)
        if contact is None:
            # Handle missing contact as a failure
            updated_run = await repo.increment_run_counts(
                tenant_id=job.tenant_id, run_id=run_id, failed=1
            )
            await self._check_run_completion(repo, job.tenant_id, run_id, updated_run)
            return

        # 5. Compliance & Suppression check
        if self._compliance is not None and contact.email:
            is_suppressed = await self._compliance.is_suppressed(
                tenant_id=job.tenant_id, channel="email", contact_identifier=contact.email
            )
            if is_suppressed:
                # Mark failed count and return (fail-closed suppressions gate)
                updated_run = await repo.increment_run_counts(
                    tenant_id=job.tenant_id, run_id=run_id, failed=1
                )
                await self._check_run_completion(repo, job.tenant_id, run_id, updated_run)
                return

        # 6. Check for mock failure request (for testing retry/failure paths)
        # Check metadata or details for fail indicator to verify counts / run status transitions
        should_fail = (
            contact.email is not None and "fail" in contact.email.lower()
        ) or contact.full_name == "MockFailContact"

        if should_fail:
            # Increment failed count and return
            updated_run = await repo.increment_run_counts(
                tenant_id=job.tenant_id, run_id=run_id, failed=1
            )
            await self._check_run_completion(repo, job.tenant_id, run_id, updated_run)
            return

        # 7. Create Mock Artifact
        findings = {
            "contact_email": contact.email,
            "company_name": contact.company_name,
            "mock_research_data": f"Mock data extracted for {contact.full_name or 'contact'}",
            "completed_at": datetime.now(UTC).isoformat(),
        }
        artifact = await repo.create_artifact(
            tenant_id=job.tenant_id,
            research_run_id=run_id,
            contact_id=contact_id,
            findings=findings,
        )

        # 8. Audit event for artifact creation
        await self._audit(
            event_type="research.artifact_created",
            tenant_id=job.tenant_id,
            actor_user_id=None,
            object_type="research_artifact",
            object_id=artifact.id,
            details={"research_run_id": str(run_id), "contact_id": str(contact_id)},
        )

        # 9. Increment processed count
        updated_run = await repo.increment_run_counts(
            tenant_id=job.tenant_id, run_id=run_id, processed=1
        )
        await self._check_run_completion(repo, job.tenant_id, run_id, updated_run)

    async def _check_run_completion(
        self,
        repo: Any,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        run: ResearchRunRecord | None,
    ) -> None:
        if run is None:
            return

        total_processed = run.processed_count + run.failed_count
        if total_processed >= run.queued_count:
            # Determine final status
            final_status = "completed"
            if run.failed_count == run.queued_count:
                final_status = "failed"
            elif run.failed_count > 0:
                # We can either mark partial failures as completed or failed.
                # Let's mark it 'completed' but check if we need run_completed/run_failed audits.
                # If there are ANY failures, let's treat it as completed if some succeeded,
                # but if ALL failed, it's failed. Let's make it fail if failed_count > 0
                # for strictness. We will mark run status 'failed' if failed_count > 0.
                final_status = "failed"

            await repo.update_run(tenant_id=tenant_id, run_id=run_id, status=final_status)

            # Audit events
            event_type = (
                "research.run_completed" if final_status == "completed" else "research.run_failed"
            )
            await self._audit(
                event_type=event_type,
                tenant_id=tenant_id,
                actor_user_id=None,
                object_type="research_run",
                object_id=run_id,
                details={
                    "processed_count": run.processed_count,
                    "failed_count": run.failed_count,
                    "queued_count": run.queued_count,
                },
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
