"""Compliance profile and suppression baseline tests (Slice 17)."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.middleware.error_handler import AppError
from app.services.compliance import (
    EMAIL,
    SMS,
    ComplianceGateService,
    ComplianceProfileRecord,
    SuppressionRecord,
    hash_contact_identifier,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_SUPPRESSION = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_NOW = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)
_RAW_EMAIL = " Lead@Example.COM "


class _ComplianceStore:
    def __init__(self) -> None:
        self.profile_row: ComplianceProfileRecord | None = None
        self.suppressions: dict[uuid.UUID, SuppressionRecord] = {}

    async def get_profile(self, tenant_id: uuid.UUID) -> ComplianceProfileRecord | None:
        if self.profile_row is None or self.profile_row.tenant_id != tenant_id:
            return None
        return self.profile_row

    async def upsert_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        jurisdiction: str,
        sending_review_required: bool,
        live_sending_allowed: bool,
        sms_allowed: bool,
    ) -> ComplianceProfileRecord:
        self.profile_row = ComplianceProfileRecord(
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            sending_review_required=sending_review_required,
            live_sending_allowed=live_sending_allowed,
            sms_allowed=sms_allowed,
        )
        return self.profile_row

    async def get_active_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
    ) -> SuppressionRecord | None:
        for row in self.suppressions.values():
            if (
                row.tenant_id == tenant_id
                and row.channel == channel
                and row.contact_hash == contact_hash
                and row.is_active()
            ):
                return row
        return None

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
        row = SuppressionRecord(
            id=_SUPPRESSION,
            tenant_id=tenant_id,
            channel=channel,
            contact_hash=contact_hash,
            reason=reason,
            source=source,
            never_contact=never_contact,
            created_at=created_at,
        )
        self.suppressions[row.id] = row
        return row

    async def revoke_suppression(
        self,
        *,
        suppression_id: uuid.UUID,
        revoked_at: datetime,
    ) -> SuppressionRecord | None:
        row = self.suppressions.get(suppression_id)
        if row is None:
            return None
        revoked = replace(row, revoked_at=revoked_at)
        self.suppressions[suppression_id] = revoked
        return revoked


async def test_default_us_compliance_profile_blocks_live_send_and_requires_review() -> None:
    service = ComplianceGateService(_ComplianceStore())

    profile = await service.profile(_TENANT)

    assert profile.jurisdiction == "US"
    assert profile.sending_review_required is True
    assert profile.live_sending_allowed is False
    assert profile.sms_allowed is False
    assert await service.requires_human_review(_TENANT) is True
    assert await service.can_live_send(tenant_id=_TENANT, channel=EMAIL) is False
    assert await service.can_live_send(tenant_id=_TENANT, channel=SMS) is False

    with pytest.raises(AppError) as exc:
        await service.require_live_send_allowed(tenant_id=_TENANT, channel=EMAIL)
    assert exc.value.status_code == 403
    assert exc.value.code == "COMPLIANCE_LIVE_SEND_DENIED"


async def test_profile_update_is_audited_without_contact_data() -> None:
    audits: list[dict[str, object]] = []

    async def audit_record(**kwargs: object) -> None:
        audits.append(kwargs)

    service = ComplianceGateService(_ComplianceStore(), audit_record=audit_record)

    profile = await service.upsert_profile(
        tenant_id=_TENANT,
        jurisdiction="US",
        sending_review_required=True,
        live_sending_allowed=False,
        sms_allowed=False,
        actor_user_id=_ACTOR,
    )

    assert profile.jurisdiction == "US"
    assert audits[0]["event_type"] == "compliance.profile_updated"
    assert _RAW_EMAIL.strip().lower() not in str(audits)


def test_contact_hash_normalizes_and_minimizes_identifier() -> None:
    a = hash_contact_identifier(channel=EMAIL, contact_identifier=" Lead@Example.COM ")
    b = hash_contact_identifier(channel=EMAIL, contact_identifier="lead@example.com")
    sms = hash_contact_identifier(channel=SMS, contact_identifier="+1 (555) 000-9999")

    assert a == b
    assert len(a) == 64
    assert len(sms) == 64
    assert "lead@example.com" not in a


async def test_suppression_never_contact_again_blocks_contact_and_audits_minimized_details() -> (
    None
):
    audits: list[dict[str, object]] = []

    async def audit_record(**kwargs: object) -> None:
        audits.append(kwargs)

    store = _ComplianceStore()
    service = ComplianceGateService(store, audit_record=audit_record)

    row = await service.add_suppression(
        tenant_id=_TENANT,
        channel=EMAIL,
        contact_identifier=_RAW_EMAIL,
        reason="never_contact_again",
        source="manual",
        now=_NOW,
        actor_user_id=_ACTOR,
    )

    assert row.never_contact is True
    assert row.contact_hash == hash_contact_identifier(channel=EMAIL, contact_identifier=_RAW_EMAIL)
    assert _RAW_EMAIL.strip().lower() not in row.contact_hash
    assert (
        await service.is_suppressed(
            tenant_id=_TENANT, channel=EMAIL, contact_identifier="lead@example.com"
        )
        is True
    )

    with pytest.raises(AppError) as exc:
        await service.require_not_suppressed(
            tenant_id=_TENANT,
            channel=EMAIL,
            contact_identifier="lead@example.com",
        )
    assert exc.value.code == "CONTACT_SUPPRESSED"
    assert _RAW_EMAIL.strip().lower() not in str(exc.value.details)
    assert audits[0]["event_type"] == "compliance.suppression_added"
    assert "contact_hash" not in str(audits)
    assert _RAW_EMAIL.strip().lower() not in str(audits)


async def test_revoked_suppression_no_longer_blocks_when_policy_allows() -> None:
    store = _ComplianceStore()
    service = ComplianceGateService(store)
    row = await service.add_suppression(
        tenant_id=_TENANT,
        channel=EMAIL,
        contact_identifier=_RAW_EMAIL,
        reason="never_contact_again",
        source="manual",
        now=_NOW,
    )

    await service.revoke_suppression(tenant_id=_TENANT, suppression_id=row.id, now=_NOW)

    assert (
        await service.is_suppressed(
            tenant_id=_TENANT, channel=EMAIL, contact_identifier="lead@example.com"
        )
        is False
    )


async def test_invalid_channel_denied_with_standard_error() -> None:
    service = ComplianceGateService(_ComplianceStore())

    with pytest.raises(AppError) as exc:
        await service.can_live_send(tenant_id=_TENANT, channel="fax")

    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_COMPLIANCE_CHANNEL"


def test_compliance_migration_shape_rls_and_minimized_storage() -> None:
    src = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0010_compliance_suppression.py"
    ).read_text(encoding="utf-8")

    assert "compliance_profiles" in src
    assert "suppressions" in src
    assert "jurisdiction" in src
    assert "sending_review_required" in src
    assert "live_sending_allowed" in src
    assert "sms_allowed" in src
    assert "contact_hash" in src
    assert "never_contact" in src
    assert "ALTER TABLE compliance_profiles ENABLE ROW LEVEL SECURITY" in src
    assert "ALTER TABLE compliance_profiles FORCE ROW LEVEL SECURITY" in src
    assert "ALTER TABLE suppressions ENABLE ROW LEVEL SECURITY" in src
    assert "ALTER TABLE suppressions FORCE ROW LEVEL SECURITY" in src
    assert "tenant_id = current_setting('app.current_tenant_id', true)::uuid" in src
    assert "raw_contact" not in src
    assert "contact_email" not in src
    assert "phone_number" not in src
    assert "twilio" not in src.lower()
    assert "stripe" not in src.lower()
