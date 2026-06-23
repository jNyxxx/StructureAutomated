"""Send gate evaluation service for Phase 1 Slice P1-09."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import (
    CAN_SCHEDULE_SEND,
    ObjectAuthorizationService,
    RBACService,
    TenantOwnedObject,
)
from app.services.billing import CAN_SEND, BillingAccessDenied, BillingGateService
from app.services.rate_limit import RateLimitPolicy, RateLimitService


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


class SendingStore(Protocol):
    async def create_gate_result(
        self,
        *,
        tenant_id: uuid.UUID,
        draft_id: uuid.UUID,
        status: str,
        deny_reason_code: str | None = None,
    ) -> Any:
        """Record send gate result."""

    async def get_outbound_message_by_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> Any | None:
        """Get outbound message for a draft."""


class DraftStore(Protocol):
    async def get_draft(self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID) -> Any | None:
        """Get draft."""


class ReviewStore(Protocol):
    async def get_review_item_for_draft(
        self, *, tenant_id: uuid.UUID, draft_id: uuid.UUID
    ) -> Any | None:
        """Get review item for a draft."""


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


class SendGateService:
    """Evaluates send gates before allowing mock message transmission."""

    def __init__(
        self,
        *,
        sending_store: SendingStore,
        draft_store: DraftStore,
        review_store: ReviewStore,
        safety_store: SafetyStore,
        contact_store: GroundingContactStore,
        billing: BillingGateService,
        rbac: RBACService,
        object_authz: ObjectAuthorizationService,
        compliance: ComplianceGate | None = None,
        rate_limiter: RateLimitService | None = None,
        rate_limit_policy: RateLimitPolicy | None = None,
        audit_record: Any = None,
    ) -> None:
        self._sending_store = sending_store
        self._draft_store = draft_store
        self._review_store = review_store
        self._safety_store = safety_store
        self._contact_store = contact_store
        self._billing = billing
        self._rbac = rbac
        self._object_authz = object_authz
        self._compliance = compliance
        self._rate_limiter = rate_limiter
        self._rate_limit_policy = rate_limit_policy
        self._audit_record = audit_record

    async def evaluate_gate(
        self,
        principal: CurrentPrincipal,
        *,
        draft_id: uuid.UUID,
        now: datetime,
    ) -> Any:
        """Evaluate if the draft meets all rules and can be sent."""
        # 1. RBAC Check
        if not self._rbac.has_permission(principal.role, CAN_SCHEDULE_SEND):
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="permission_denied",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "permission_denied"},
            )
            raise AppError("FORBIDDEN", "RBAC permission denied.", status_code=403)

        # 2. Billing Check
        if not await self._billing.has_feature(principal.tenant_id, CAN_SEND, now=now):
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="billing_blocked",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "billing_blocked"},
            )
            raise BillingAccessDenied(code="BILLING_FEATURE_DENIED")

        # 3. Retrieve Draft & Object Auth Check
        draft = await self._draft_store.get_draft(tenant_id=principal.tenant_id, draft_id=draft_id)
        if draft is None:
            raise AppError("DRAFT_NOT_FOUND", "Draft not found.", status_code=404)

        if draft.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        self._object_authz.require_tenant_owner(
            principal=principal,
            obj=TenantOwnedObject(id=draft.id, tenant_id=draft.tenant_id),
        )

        # 4. Draft Status Constraint
        if draft.status not in ("generated", "approved"):
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="invalid_draft_state",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "invalid_draft_state", "status": draft.status},
            )
            raise AppError(
                "INVALID_DRAFT_STATE",
                f"Draft status '{draft.status}' is invalid for sending.",
                status_code=400,
            )

        # 5. Review Queue Gate
        review_item = await self._review_store.get_review_item_for_draft(
            tenant_id=principal.tenant_id, draft_id=draft_id
        )
        if review_item is None:
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="review_not_approved",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "review_not_approved", "error": "missing_review"},
            )
            raise AppError("REVIEW_NOT_APPROVED", "Draft has not been reviewed.", status_code=400)

        if review_item.status != "approved":
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="review_not_approved",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "review_not_approved", "status": review_item.status},
            )
            raise AppError(
                "REVIEW_NOT_APPROVED",
                f"Review item status is '{review_item.status}', not approved.",
                status_code=400,
            )

        # 6. Tenant & Model consistency checking
        if (
            review_item.tenant_id != draft.tenant_id
            or review_item.campaign_id != draft.campaign_id
            or review_item.contact_id != draft.contact_id
        ):
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="tenant_mismatch",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "tenant_mismatch"},
            )
            raise AppError(
                "DRAFT_MISMATCH", "Review item properties do not match draft.", status_code=400
            )

        # 7. Compliance check (Suppression gate)
        contact = await self._contact_store.get_contact(
            tenant_id=principal.tenant_id, contact_id=draft.contact_id
        )
        if contact is None:
            raise AppError("CONTACT_NOT_FOUND", "Contact not found.", status_code=404)
        if contact.tenant_id != principal.tenant_id:
            raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

        if self._compliance is not None and contact.email:
            is_suppressed = await self._compliance.is_suppressed(
                tenant_id=principal.tenant_id,
                channel="email",
                contact_identifier=contact.email,
            )
            if is_suppressed:
                await self._sending_store.create_gate_result(
                    tenant_id=principal.tenant_id,
                    draft_id=draft_id,
                    status="denied",
                    deny_reason_code="contact_suppressed",
                )
                await self._audit(
                    event_type="send_gate.failed",
                    tenant_id=principal.tenant_id,
                    actor_user_id=principal.user_id,
                    object_type="draft",
                    object_id=draft_id,
                    details={"reason": "contact_suppressed"},
                )
                raise AppError(
                    "COMPLIANCE_SUPPRESSED",
                    "Cannot send draft for a suppressed contact.",
                    status_code=400,
                )

        # 8. Safety & Groundedness Checks
        safety_results = await self._safety_store.list_results_for_context(
            tenant_id=principal.tenant_id,
            draft_id=draft_id,
        )

        has_prompt_injection = False
        has_source_trust = False
        has_groundedness = False

        for res in safety_results:
            if res.tenant_id != principal.tenant_id:
                raise AppError("FORBIDDEN", "Tenant mismatch.", status_code=403)

            if res.status == "failed":
                code = "safety_failed"
                if res.gate_type == "groundedness":
                    code = "groundedness_failed"
                await self._sending_store.create_gate_result(
                    tenant_id=principal.tenant_id,
                    draft_id=draft_id,
                    status="denied",
                    deny_reason_code=code,
                )
                await self._audit(
                    event_type="send_gate.failed",
                    tenant_id=principal.tenant_id,
                    actor_user_id=principal.user_id,
                    object_type="draft",
                    object_id=draft_id,
                    details={"reason": code, "gate_type": res.gate_type},
                )
                raise AppError(
                    "SAFETY_GATE_FAILED", f"Safety gate '{res.gate_type}' failed.", status_code=400
                )

            if res.gate_type == "prompt_injection":
                has_prompt_injection = True
            elif res.gate_type == "source_trust":
                has_source_trust = True
            elif res.gate_type == "groundedness":
                if res.status != "passed":
                    await self._sending_store.create_gate_result(
                        tenant_id=principal.tenant_id,
                        draft_id=draft_id,
                        status="denied",
                        deny_reason_code="groundedness_failed",
                    )
                    await self._audit(
                        event_type="send_gate.failed",
                        tenant_id=principal.tenant_id,
                        actor_user_id=principal.user_id,
                        object_type="draft",
                        object_id=draft_id,
                        details={"reason": "groundedness_failed"},
                    )
                    raise AppError(
                        "SAFETY_GATE_FAILED",
                        "Groundedness gate must pass for sending.",
                        status_code=400,
                    )
                has_groundedness = True

        if not has_prompt_injection:
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="safety_missing",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "safety_missing", "gate_type": "prompt_injection"},
            )
            raise AppError(
                "SAFETY_GATE_MISSING",
                "Required prompt_injection gate evaluation is missing.",
                status_code=400,
            )

        if not has_source_trust:
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="safety_missing",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "safety_missing", "gate_type": "source_trust"},
            )
            raise AppError(
                "SAFETY_GATE_MISSING",
                "Required source_trust gate evaluation is missing.",
                status_code=400,
            )

        if not has_groundedness:
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="groundedness_missing",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "groundedness_missing"},
            )
            raise AppError(
                "SAFETY_GATE_MISSING",
                "Required groundedness gate evaluation is missing.",
                status_code=400,
            )

        # 9. Duplicate Send Check
        existing_msg = await self._sending_store.get_outbound_message_by_draft(
            tenant_id=principal.tenant_id, draft_id=draft_id
        )
        if existing_msg is not None:
            await self._sending_store.create_gate_result(
                tenant_id=principal.tenant_id,
                draft_id=draft_id,
                status="denied",
                deny_reason_code="duplicate_send",
            )
            await self._audit(
                event_type="send_gate.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_type="draft",
                object_id=draft_id,
                details={"reason": "duplicate_send"},
            )
            raise AppError(
                "DUPLICATE_SEND", "Draft has already been sent or queued.", status_code=409
            )

        # 10. Rate Limiting Check (Throttling)
        if self._rate_limiter is not None and self._rate_limit_policy is not None:
            rl_res = await self._rate_limiter.check(
                self._rate_limit_policy,
                tenant_id=str(principal.tenant_id),
                now=now,
            )
            if not rl_res.allowed:
                await self._sending_store.create_gate_result(
                    tenant_id=principal.tenant_id,
                    draft_id=draft_id,
                    status="denied",
                    deny_reason_code="throttled",
                )
                await self._audit(
                    event_type="send_gate.failed",
                    tenant_id=principal.tenant_id,
                    actor_user_id=principal.user_id,
                    object_type="draft",
                    object_id=draft_id,
                    details={"reason": "throttled"},
                )
                raise AppError("RATE_LIMITED", "Sending rate limit exceeded.", status_code=429)

        # All gates passed
        res = await self._sending_store.create_gate_result(
            tenant_id=principal.tenant_id,
            draft_id=draft_id,
            status="passed",
        )
        await self._audit(
            event_type="send_gate.passed",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_type="draft",
            object_id=draft_id,
            details={},
        )
        return res

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
