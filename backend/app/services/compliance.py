"""Central compliance profile and suppression gates (Slice 17).

No real sending is implemented. Live sending remains denied by default and gated
behind compliance review + owner approval. Contact identifiers are normalized and
hashed so raw contact data does not enter suppression storage/audit/errors.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.middleware.error_handler import AppError

EMAIL = "email"
SMS = "sms"
CHANNELS = (EMAIL, SMS)
DEFAULT_JURISDICTION = "US"


class ComplianceDenied(AppError):
    def __init__(
        self, *, code: str = "COMPLIANCE_DENIED", message: str = "Compliance denied."
    ) -> None:
        super().__init__(code, message, status_code=403)


@dataclass(frozen=True)
class ComplianceProfileRecord:
    tenant_id: uuid.UUID
    jurisdiction: str = DEFAULT_JURISDICTION
    sending_review_required: bool = True
    live_sending_allowed: bool = False
    sms_allowed: bool = False


@dataclass(frozen=True)
class SuppressionRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    channel: str
    contact_hash: str
    reason: str
    source: str
    never_contact: bool
    created_at: datetime
    revoked_at: datetime | None = None

    def is_active(self) -> bool:
        return self.revoked_at is None


class ComplianceStore(Protocol):
    async def get_profile(self, tenant_id: uuid.UUID) -> ComplianceProfileRecord | None:
        """Return tenant compliance profile, if one exists."""

    async def upsert_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        jurisdiction: str,
        sending_review_required: bool,
        live_sending_allowed: bool,
        sms_allowed: bool,
    ) -> ComplianceProfileRecord:
        """Create or update a profile."""

    async def get_active_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
    ) -> SuppressionRecord | None:
        """Return an active suppression record."""

    async def add_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
        reason: str,
        source: str,
        never_contact: bool,
        created_at: datetime,
    ) -> SuppressionRecord:
        """Add a minimized suppression record."""

    async def revoke_suppression(
        self,
        *,
        suppression_id: uuid.UUID,
        revoked_at: datetime,
    ) -> SuppressionRecord | None:
        """Revoke a suppression record only when policy allows."""


AuditRecorder = Callable[..., Awaitable[None]]


def normalize_contact_identifier(*, channel: str, contact_identifier: str) -> str:
    value = contact_identifier.strip()
    if channel == EMAIL:
        return value.lower()
    if channel == SMS:
        return "".join(ch for ch in value if ch.isdigit())
    return value.lower()


def hash_contact_identifier(*, channel: str, contact_identifier: str) -> str:
    normalized = normalize_contact_identifier(
        channel=channel, contact_identifier=contact_identifier
    )
    return hashlib.sha256(f"{channel}:{normalized}".encode()).hexdigest()


def _validate_channel(channel: str) -> None:
    if channel not in CHANNELS:
        raise AppError("INVALID_COMPLIANCE_CHANNEL", "Invalid compliance channel.", status_code=400)


class ComplianceGateService:
    """Central compliance and suppression gates. Deny live/suppressed by default."""

    def __init__(self, store: ComplianceStore, audit_record: AuditRecorder | None = None) -> None:
        self._store = store
        self._audit_record = audit_record

    async def profile(self, tenant_id: uuid.UUID) -> ComplianceProfileRecord:
        return await self._store.get_profile(tenant_id) or ComplianceProfileRecord(
            tenant_id=tenant_id
        )

    async def upsert_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        jurisdiction: str = DEFAULT_JURISDICTION,
        sending_review_required: bool = True,
        live_sending_allowed: bool = False,
        sms_allowed: bool = False,
        actor_user_id: uuid.UUID | None = None,
    ) -> ComplianceProfileRecord:
        record = await self._store.upsert_profile(
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            sending_review_required=sending_review_required,
            live_sending_allowed=live_sending_allowed,
            sms_allowed=sms_allowed,
        )
        if self._audit_record is not None:
            await self._audit_record(
                event_type="compliance.profile_updated",
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                details={
                    "jurisdiction": jurisdiction,
                    "sending_review_required": sending_review_required,
                    "live_sending_allowed": live_sending_allowed,
                    "sms_allowed": sms_allowed,
                },
            )
        return record

    async def requires_human_review(self, tenant_id: uuid.UUID) -> bool:
        return (await self.profile(tenant_id)).sending_review_required

    async def can_live_send(self, *, tenant_id: uuid.UUID, channel: str) -> bool:
        _validate_channel(channel)
        profile = await self.profile(tenant_id)
        if not profile.live_sending_allowed:
            return False
        if channel == SMS and not profile.sms_allowed:
            return False
        return True

    async def require_live_send_allowed(self, *, tenant_id: uuid.UUID, channel: str) -> None:
        if not await self.can_live_send(tenant_id=tenant_id, channel=channel):
            raise ComplianceDenied(code="COMPLIANCE_LIVE_SEND_DENIED")

    async def is_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> bool:
        _validate_channel(channel)
        contact_hash = hash_contact_identifier(
            channel=channel, contact_identifier=contact_identifier
        )
        row = await self._store.get_active_suppression(
            tenant_id=tenant_id, channel=channel, contact_hash=contact_hash
        )
        return row is not None

    async def require_not_suppressed(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
    ) -> None:
        if await self.is_suppressed(
            tenant_id=tenant_id,
            channel=channel,
            contact_identifier=contact_identifier,
        ):
            raise ComplianceDenied(code="CONTACT_SUPPRESSED", message="Contact is suppressed.")

    async def add_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_identifier: str,
        reason: str,
        source: str,
        now: datetime,
        actor_user_id: uuid.UUID | None = None,
        never_contact: bool = True,
    ) -> SuppressionRecord:
        _validate_channel(channel)
        contact_hash = hash_contact_identifier(
            channel=channel, contact_identifier=contact_identifier
        )
        record = await self._store.add_suppression(
            tenant_id=tenant_id,
            channel=channel,
            contact_hash=contact_hash,
            reason=reason,
            source=source,
            never_contact=never_contact,
            created_at=now,
        )
        if self._audit_record is not None:
            await self._audit_record(
                event_type="compliance.suppression_added",
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                object_type="suppression",
                object_id=record.id,
                details={"channel": channel, "reason": reason, "source": source},
            )
        return record

    async def revoke_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        suppression_id: uuid.UUID,
        now: datetime,
        actor_user_id: uuid.UUID | None = None,
    ) -> SuppressionRecord:
        record = await self._store.revoke_suppression(
            suppression_id=suppression_id,
            revoked_at=now,
        )
        if record is None or record.tenant_id != tenant_id:
            raise ComplianceDenied(code="SUPPRESSION_NOT_FOUND", message="Suppression not found.")
        if self._audit_record is not None:
            await self._audit_record(
                event_type="compliance.suppression_revoked",
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                object_type="suppression",
                object_id=record.id,
                details={"channel": record.channel, "reason": record.reason},
            )
        return record
