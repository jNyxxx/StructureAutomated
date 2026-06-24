"""Human review queue service for Phase 1 Slice P1-08."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import CAN_APPROVE_DRAFT, CAN_REVIEW_DRAFT, RBACService
from app.services.billing import CAN_RUN_AGENTS, BillingGateService
from app.services.idempotency import IdempotencyOutcome, IdempotencyState


class GroundingContactStore(Protocol):
    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        """Retrieve contact details."""


class ComplianceGate(Protocol):
    async def is_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> bool:
        """Check if contact identifier is suppressed."""


class ReviewStore(Protocol):
    async def create_review_item(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str = "pending_review",
    ) -> Any:
        """Create review item."""

    async def get_review_item(self, *, tenant_id: uuid.UUID, review_id: uuid.UUID) -> Any | None:
        """Get review item by ID."""

    async def update_review_status(
        self,
        *,
        tenant_id: uuid.UUID,
        review_id: uuid.UUID,
        status: str,
        reviewer_user_id: uuid.UUID | None = None,
        action_reason: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> Any | None:
        """Update status."""

    async def list_review_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[Any]:
        """List queue."""


class DraftStore(Protocol):
    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> Any | None:
        """Get draft."""

    async def update_draft_status(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID, status: str
    ) -> Any | None:
        """Update draft status."""


class SafetyStore(Protocol):
    async def list_results_for_context(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> list[Any]:
        """List safety results."""


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


@dataclass(frozen=True)
class ReviewActionResult:
    review_item: Any | None
    idempotency_replay: bool = False


class ReviewService:
    """Service managing human review queue workflows."""

    def __init__(
        self,
        *,
        review_store: ReviewStore,
        draft_store: DraftStore,
        safety_store: SafetyStore,
        contact_store: GroundingContactStore,
        billing: BillingGateService,
        rbac: RBACService,
        compliance: ComplianceGate | None = None,
        idempotency: IdempotencyGate | None = None,
        audit_record: Any = None,
    ) -> None:
        self._review_store = review_store
        self._draft_store = draft_store
        self._safety_store = safety_store
        self._contact_store = contact_store
        self._billing = billing
        self._rbac = rbac
        self._compliance = compliance
        self._idempotency = idempotency
        self._audit_record = audit_record

    async def list_review_queue(
        self,
        principal: CurrentPrincipal,
        *,
        campaign_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[Any]:
        """List pending review items in the tenant queue.

        Note: This is a read-only queue listing operation and does not trigger
        any outbound actions or AI agent loops, so the CAN_RUN_AGENTS billing check
        is intentionally omitted here.
        """
        self._rbac.require(principal, CAN_REVIEW_DRAFT)
        return await self._review_store.list_review_queue(
            tenant_id=principal.tenant_id,
            campaign_id=campaign_id,
            status=status,
        )

    async def _run_idempotent_action(
        self,
        *,
        principal: CurrentPrincipal,
        review_id: uuid.UUID,
        action: str,
        idempotency_key: str | None,
        now: datetime,
        reason: str | None = None,
    ) -> ReviewActionResult:
        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "review_id": str(review_id),
            "action": action,
            "reason": reason,
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
                return ReviewActionResult(review_item=None, idempotency_replay=True)
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "REVIEW_ACTION_IN_PROGRESS",
                    "Review action is already in progress.",
                    status_code=409,
                )

        if action == "approve":
            item = await self.approve_draft(principal, review_id=review_id, now=now)
        elif action == "reject":
            item = await self.reject_draft(principal, review_id=review_id, reason=reason, now=now)
        elif action == "request_regeneration":
            item = await self.request_regeneration(
                principal, review_id=review_id, reason=reason, now=now
            )
        else:
            raise AppError("INVALID_REVIEW_ACTION", "Invalid review action.", status_code=400)

        if self._idempotency is not None and idempotency_key is not None:
            await self._idempotency.complete(
                key=idempotency_key,
                response_payload={
                    "review_id": str(review_id),
                    "action": action,
                    "review_item_id": str(item.id) if item is not None else None,
                },
                status_code=200,
                tenant_id=principal.tenant_id,
            )
        return ReviewActionResult(review_item=item)

    async def approve_draft_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        review_id: uuid.UUID,
        idempotency_key: str | None,
        now: datetime,
    ) -> ReviewActionResult:
        return await self._run_idempotent_action(
            principal=principal,
            review_id=review_id,
            action="approve",
            idempotency_key=idempotency_key,
            now=now,
        )

    async def reject_draft_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        review_id: uuid.UUID,
        reason: str | None = None,
        idempotency_key: str | None,
        now: datetime,
    ) -> ReviewActionResult:
        return await self._run_idempotent_action(
            principal=principal,
            review_id=review_id,
            action="reject",
            idempotency_key=idempotency_key,
            now=now,
            reason=reason,
        )

    async def request_regeneration_idempotent(
        self,
        principal: CurrentPrincipal,
        *,
        review_id: uuid.UUID,
        reason: str | None = None,
        idempotency_key: str | None,
        now: datetime,
    ) -> ReviewActionResult:
        return await self._run_idempotent_action(
            principal=principal,
            review_id=review_id,
            action="request_regeneration",
            idempotency_key=idempotency_key,
            now=now,
            reason=reason,
        )

    async def approve_draft(
        self,
        principal: CurrentPrincipal,
        *,
        review_id: uuid.UUID,
        now: datetime,
    ) -> Any:
        """Approve a draft email for sending."""
        # 1. RBAC Gate
        self._rbac.require(principal, CAN_APPROVE_DRAFT)

        # 2. Billing Gate
        await self._billing.require_feature(principal.tenant_id, CAN_RUN_AGENTS, now=now)

        # 3. Retrieve Review Item & check tenant boundary
        item = await self._review_store.get_review_item(
            tenant_id=principal.tenant_id, review_id=review_id
        )
        if item is None:
            raise AppError("REVIEW_ITEM_NOT_FOUND", "Review item not found.", status_code=404)
        if item.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        if item.status != "pending_review":
            raise AppError(
                "INVALID_REVIEW_STATE", "Review item is not pending review.", status_code=400
            )

        # 4. Retrieve Draft & check tenant boundary
        draft = await self._draft_store.get_draft(
            tenant_id=principal.tenant_id, draft_id=item.draft_id
        )
        if draft is None:
            raise AppError("DRAFT_NOT_FOUND", "Draft not found.", status_code=404)
        if draft.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        # Ensure review item fields match actual draft details
        if (
            draft.tenant_id != item.tenant_id
            or draft.campaign_id != item.campaign_id
            or draft.contact_id != item.contact_id
        ):
            raise AppError(
                "DRAFT_MISMATCH",
                "Draft properties do not match review item.",
                status_code=400,
            )

        if draft.status != "generated":
            raise AppError(
                "INVALID_DRAFT_STATE",
                f"Cannot approve draft in state: {draft.status}",
                status_code=400,
            )

        # 5. Compliance Check (Suppression Gate)
        if self._compliance is not None:
            contact = await self._contact_store.get_contact(
                tenant_id=principal.tenant_id, contact_id=item.contact_id
            )
            if contact is None:
                raise AppError("CONTACT_NOT_FOUND", "Contact not found.", status_code=404)
            if contact.tenant_id != principal.tenant_id:
                raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

            if contact.email:
                is_suppressed = await self._compliance.is_suppressed(
                    tenant_id=principal.tenant_id,
                    channel="email",
                    contact_identifier=contact.email,
                )
                if is_suppressed:
                    raise AppError(
                        "COMPLIANCE_SUPPRESSED",
                        "Cannot approve draft for a suppressed contact.",
                        status_code=400,
                    )

        # 6. Safety & Groundedness Gate Check
        results = await self._safety_store.list_results_for_context(
            tenant_id=principal.tenant_id,
            draft_id=item.draft_id,
        )

        has_prompt_injection = False
        has_source_trust = False
        has_groundedness = False

        for res in results:
            if res.tenant_id != principal.tenant_id:
                raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

            if res.status == "failed":
                raise AppError(
                    "SAFETY_GATE_FAILED",
                    f"Safety check '{res.gate_type}' failed for this draft.",
                    status_code=400,
                )

            if res.gate_type == "prompt_injection":
                has_prompt_injection = True
            elif res.gate_type == "source_trust":
                has_source_trust = True
            elif res.gate_type == "groundedness":
                if res.status != "passed":
                    raise AppError(
                        "SAFETY_GATE_FAILED",
                        "Groundedness gate must pass for approval.",
                        status_code=400,
                    )
                has_groundedness = True

        if not has_prompt_injection:
            raise AppError(
                "SAFETY_GATE_MISSING",
                "Required prompt_injection gate evaluation is missing.",
                status_code=400,
            )
        if not has_source_trust:
            raise AppError(
                "SAFETY_GATE_MISSING",
                "Required source_trust gate evaluation is missing.",
                status_code=400,
            )
        if not has_groundedness:
            raise AppError(
                "SAFETY_GATE_MISSING",
                "Required groundedness gate evaluation is missing.",
                status_code=400,
            )

        # 7. Update Review Status
        updated_item = await self._review_store.update_review_status(
            tenant_id=principal.tenant_id,
            review_id=review_id,
            status="approved",
            reviewer_user_id=principal.user_id,
            reviewed_at=now,
        )

        # 8. Record audit log
        await self._audit(
            event_type="draft.approved",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="review_item",
            object_id=review_id,
            details={"draft_id": str(item.draft_id)},
        )

        return updated_item

    async def reject_draft(
        self,
        principal: CurrentPrincipal,
        *,
        review_id: uuid.UUID,
        reason: str | None = None,
        now: datetime,
    ) -> Any:
        """Reject a draft email from queue.

        Note: Rejecting a draft manual workflow termination does not trigger
        any outbound actions or AI agent loops, so the CAN_RUN_AGENTS billing check
        is intentionally omitted here.
        """
        self._rbac.require(principal, CAN_REVIEW_DRAFT)

        item = await self._review_store.get_review_item(
            tenant_id=principal.tenant_id, review_id=review_id
        )
        if item is None:
            raise AppError("REVIEW_ITEM_NOT_FOUND", "Review item not found.", status_code=404)
        if item.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        if item.status != "pending_review":
            raise AppError(
                "INVALID_REVIEW_STATE", "Review item is not pending review.", status_code=400
            )

        updated_item = await self._review_store.update_review_status(
            tenant_id=principal.tenant_id,
            review_id=review_id,
            status="rejected",
            reviewer_user_id=principal.user_id,
            action_reason=reason,
            reviewed_at=now,
        )

        await self._audit(
            event_type="draft.rejected",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="review_item",
            object_id=review_id,
            details={"draft_id": str(item.draft_id), "reason": reason or ""},
        )

        return updated_item

    async def request_regeneration(
        self,
        principal: CurrentPrincipal,
        *,
        review_id: uuid.UUID,
        reason: str | None = None,
        now: datetime,
    ) -> Any:
        """Request AI regeneration of a draft email."""
        self._rbac.require(principal, CAN_REVIEW_DRAFT)

        # Billing Gate (since regeneration triggers a new AI agent loop to rebuild the draft)
        await self._billing.require_feature(principal.tenant_id, CAN_RUN_AGENTS, now=now)

        item = await self._review_store.get_review_item(
            tenant_id=principal.tenant_id, review_id=review_id
        )
        if item is None:
            raise AppError("REVIEW_ITEM_NOT_FOUND", "Review item not found.", status_code=404)
        if item.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        if item.status != "pending_review":
            raise AppError(
                "INVALID_REVIEW_STATE", "Review item is not pending review.", status_code=400
            )

        # Update review item status
        updated_item = await self._review_store.update_review_status(
            tenant_id=principal.tenant_id,
            review_id=review_id,
            status="regeneration_requested",
            reviewer_user_id=principal.user_id,
            action_reason=reason,
            reviewed_at=now,
        )

        # Update draft status
        await self._draft_store.update_draft_status(
            tenant_id=principal.tenant_id,
            draft_id=item.draft_id,
            status="needs_regeneration",
        )

        await self._audit(
            event_type="draft.needs_regeneration",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="review_item",
            object_id=review_id,
            details={"draft_id": str(item.draft_id), "reason": reason or ""},
        )

        return updated_item

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
