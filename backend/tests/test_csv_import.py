"""CRE contact CSV import foundation tests (Phase 1 P1-01)."""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.models import Contact, ContactImport, ContactImportRow
from app.services.authz import CAN_IMPORT_CONTACTS, RBACService
from app.services.billing import (
    CAN_CREATE_CAMPAIGN,
    BillingGateService,
    BillingPlan,
    TenantSubscriptionRecord,
)
from app.services.compliance import (
    EMAIL,
    ComplianceGateService,
    ComplianceProfileRecord,
    SuppressionRecord,
    hash_contact_identifier,
)
from app.services.csv_import import (
    ContactImportRecord,
    ContactImportResult,
    ContactImportRowRecord,
    ContactRecord,
    CsvImportService,
    ParsedContactRow,
    build_dedupe_hash,
    parse_contact_csv,
)
from app.services.idempotency import IdempotencyOutcome, IdempotencyState

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_ACTOR = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_NOW = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
_PLAN_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


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
        if tenant_id != self.record.tenant_id:
            return None
        return self.record

    async def set_status(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None,
    ) -> TenantSubscriptionRecord:
        raise AssertionError("not used by CSV import tests")


class _ComplianceStore:
    def __init__(self, *, suppressed_email: str | None = None) -> None:
        self.suppressed_email = suppressed_email

    async def get_profile(self, tenant_id: uuid.UUID) -> ComplianceProfileRecord | None:
        return None

    async def upsert_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        jurisdiction: str,
        sending_review_required: bool,
        live_sending_allowed: bool,
        sms_allowed: bool,
    ) -> ComplianceProfileRecord:
        return ComplianceProfileRecord(
            tenant_id=tenant_id,
            jurisdiction=jurisdiction,
            sending_review_required=sending_review_required,
            live_sending_allowed=live_sending_allowed,
            sms_allowed=sms_allowed,
        )

    async def get_active_suppression(
        self,
        *,
        tenant_id: uuid.UUID,
        channel: str,
        contact_hash: str,
    ) -> SuppressionRecord | None:
        if self.suppressed_email is None:
            return None
        expected = hash_contact_identifier(channel=EMAIL, contact_identifier=self.suppressed_email)
        if tenant_id == _TENANT and channel == EMAIL and contact_hash == expected:
            return SuppressionRecord(
                id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                tenant_id=tenant_id,
                channel=channel,
                contact_hash=contact_hash,
                reason="never_contact_again",
                source="manual",
                never_contact=True,
                created_at=_NOW,
            )
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
        raise AssertionError("not used by CSV import tests")

    async def revoke_suppression(
        self,
        *,
        suppression_id: uuid.UUID,
        revoked_at: datetime,
    ) -> SuppressionRecord | None:
        return None


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
        self.imports: dict[uuid.UUID, ContactImportRecord] = {}
        self.contacts: dict[tuple[uuid.UUID, str], ContactRecord] = {}
        self.rows: list[ContactImportRowRecord] = []
        self.expected_tenant_id = _TENANT
        self._import_id = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        self._next = 1

    def _assert_tenant(self, tenant_id: uuid.UUID) -> None:
        assert tenant_id == self.expected_tenant_id

    def _id(self) -> uuid.UUID:
        value = uuid.UUID(f"00000000-0000-0000-0000-{self._next:012d}")
        self._next += 1
        return value

    async def create_import(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        idempotency_key: str,
        source_filename: str | None,
        status: str,
    ) -> ContactImportRecord:
        self._assert_tenant(tenant_id)
        record = ContactImportRecord(
            id=self._import_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            status=status,
        )
        self.imports[record.id] = record
        return record

    async def update_import_status(
        self,
        *,
        import_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str,
        total_rows: int,
        valid_rows: int,
        invalid_rows: int,
        duplicate_rows: int,
        completed_at: datetime | None,
        failed_at: datetime | None,
    ) -> ContactImportRecord:
        self._assert_tenant(tenant_id)
        record = ContactImportRecord(
            id=import_id,
            tenant_id=tenant_id,
            idempotency_key=self.imports[import_id].idempotency_key,
            status=status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            duplicate_rows=duplicate_rows,
        )
        self.imports[import_id] = record
        return record

    async def find_contact_by_dedupe_hash(
        self, *, tenant_id: uuid.UUID, dedupe_hash: str
    ) -> ContactRecord | None:
        self._assert_tenant(tenant_id)
        return self.contacts.get((tenant_id, dedupe_hash))

    async def create_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        source_import_id: uuid.UUID,
        row: ParsedContactRow,
    ) -> ContactRecord:
        self._assert_tenant(tenant_id)
        assert row.dedupe_hash is not None
        contact = ContactRecord(
            id=self._id(),
            tenant_id=tenant_id,
            dedupe_hash=row.dedupe_hash,
            normalized_email=row.normalized_email,
            normalized_domain=row.normalized_domain,
            normalized_company=row.normalized_company,
            full_name=row.full_name,
            title=row.title,
            email=row.email,
            domain=row.domain,
            company_name=row.company_name,
        )
        self.contacts[(tenant_id, row.dedupe_hash)] = contact
        return contact

    async def create_import_row(
        self,
        *,
        tenant_id: uuid.UUID,
        import_id: uuid.UUID,
        row: ParsedContactRow,
        status: str,
        validation_errors: tuple[str, ...],
        contact_id: uuid.UUID | None,
    ) -> ContactImportRowRecord:
        self._assert_tenant(tenant_id)
        record = ContactImportRowRecord(
            id=self._id(),
            tenant_id=tenant_id,
            import_id=import_id,
            row_number=row.row_number,
            row_hash=row.row_hash,
            status=status,
            validation_errors=validation_errors,
            contact_id=contact_id,
            dedupe_hash=row.dedupe_hash,
        )
        self.rows.append(record)
        return record


def _service(
    store: _Store,
    *,
    billing_allowed: bool = True,
    suppressed_email: str | None = None,
    idempotency: _IdempotencyGate | None = None,
    audits: list[dict[str, Any]] | None = None,
) -> CsvImportService:
    async def audit_record(**kwargs: Any) -> None:
        if audits is not None:
            audits.append(kwargs)

    return CsvImportService(
        store=store,
        rbac=RBACService(),
        billing=BillingGateService(_BillingStore(allowed=billing_allowed)),
        compliance=ComplianceGateService(_ComplianceStore(suppressed_email=suppressed_email)),
        idempotency=idempotency,
        audit_record=audit_record,
    )


async def _import(
    service: CsvImportService,
    *,
    csv_text: str,
    principal: CurrentPrincipal | None = None,
    idempotency_key: str = "import-key-1",
) -> ContactImportResult:
    return await service.import_contacts(
        principal=principal or _principal(),
        csv_text=csv_text,
        source_filename="cre-import.csv",
        idempotency_key=idempotency_key,
        now=_NOW,
    )


def test_contact_import_models_are_tenant_owned_and_constrained() -> None:
    for model in (Contact, ContactImport, ContactImportRow):
        assert model.__table__.c.tenant_id.nullable is False

    contact_import_table: Any = ContactImport.__table__
    contact_import_row_table: Any = ContactImportRow.__table__
    contact_table: Any = Contact.__table__
    import_checks = [
        str(c.sqltext) for c in contact_import_table.constraints if isinstance(c, CheckConstraint)
    ]
    row_checks = [
        str(c.sqltext)
        for c in contact_import_row_table.constraints
        if isinstance(c, CheckConstraint)
    ]
    contact_uniques = [
        frozenset(col.name for col in c.columns)
        for c in contact_table.constraints
        if isinstance(c, UniqueConstraint)
    ]

    assert any("pending" in check and "failed" in check for check in import_checks)
    assert any("invalid" in check and "duplicate" in check for check in row_checks)
    assert frozenset({"tenant_id", "dedupe_hash"}) in contact_uniques


def test_central_rbac_import_permission_allows_import_roles_and_denies_unknown() -> None:
    rbac = RBACService()

    assert rbac.has_permission("owner", CAN_IMPORT_CONTACTS) is True
    assert rbac.has_permission("admin", CAN_IMPORT_CONTACTS) is True
    assert rbac.has_permission("marketer", CAN_IMPORT_CONTACTS) is True
    assert rbac.has_permission("viewer", CAN_IMPORT_CONTACTS) is False
    assert rbac.has_permission("owner", "contacts:unknown") is False

    with pytest.raises(AppError) as exc:
        rbac.require(_principal("owner"), "contacts:unknown")
    assert exc.value.code == "FORBIDDEN"


def test_parse_contact_csv_normalizes_and_uses_tenant_scoped_dedupe_hash() -> None:
    csv_text = "name,email,company,domain\nJane Doe, Jane@Example.COM ,Acme CRE,https://www.acme.com/path\n"

    row = parse_contact_csv(csv_text, tenant_id=_TENANT)[0]
    other = parse_contact_csv(csv_text, tenant_id=_OTHER_TENANT)[0]

    assert row.normalized_email == "jane@example.com"
    assert row.normalized_domain == "acme.com"
    assert row.normalized_company == "acme cre"
    assert row.dedupe_hash != other.dedupe_hash
    assert "jane@example.com" not in str(row.dedupe_hash)


async def test_allowed_role_can_import_contacts_through_central_rbac_gate() -> None:
    store = _Store()
    service = _service(store)

    result = await _import(
        service,
        principal=_principal("marketer"),
        csv_text="name,email,company,domain\nMarketer,m@example.com,Acme,acme.com\n",
    )

    assert result.import_record is not None
    assert result.import_record.status == "completed"
    assert len(store.contacts) == 1


async def test_valid_csv_import_creates_contacts_rows_idempotency_and_audit() -> None:
    store = _Store()
    idempotency = _IdempotencyGate()
    audits: list[dict[str, Any]] = []
    service = _service(store, idempotency=idempotency, audits=audits)

    result = await _import(
        service,
        csv_text="name,email,company,domain\nJane Doe,jane@example.com,Acme,acme.com\n",
    )

    assert result.import_record is not None
    assert result.import_record.status == "completed"
    assert result.import_record.total_rows == 1
    assert result.import_record.valid_rows == 1
    assert result.import_record.invalid_rows == 0
    assert result.import_record.duplicate_rows == 0
    assert [row.status for row in result.rows] == ["imported"]
    assert len(store.contacts) == 1
    assert idempotency.begin_calls[0]["tenant_id"] == _TENANT
    assert idempotency.complete_calls[0]["status_code"] == 201
    assert [audit["event_type"] for audit in audits] == [
        "contact_import.created",
        "contact_import.completed",
    ]
    assert "jane@example.com" not in str(audits)


async def test_invalid_rows_are_captured_without_creating_contacts() -> None:
    store = _Store()
    service = _service(store)

    result = await _import(
        service,
        csv_text="name,email,company,domain\nNope,not-an-email,,bad domain\nBlank,,,\n",
    )

    assert result.import_record is not None
    assert result.import_record.total_rows == 2
    assert result.import_record.valid_rows == 0
    assert result.import_record.invalid_rows == 2
    assert len(store.contacts) == 0
    assert result.rows[0].validation_errors == (
        "invalid_email",
        "invalid_domain",
        "missing_dedupe_key",
    )
    assert "missing_contact_identity" in result.rows[1].validation_errors


async def test_duplicate_rows_are_handled_by_tenant_dedupe() -> None:
    store = _Store()
    service = _service(store)

    result = await _import(
        service,
        csv_text=(
            "name,email,company,domain\n"
            "Jane,jane@example.com,Acme,acme.com\n"
            "Jane Copy,JANE@example.com,Acme,acme.com\n"
        ),
    )

    assert result.import_record is not None
    assert result.import_record.valid_rows == 1
    assert result.import_record.duplicate_rows == 1
    assert [row.status for row in result.rows] == ["imported", "duplicate"]
    assert len(store.contacts) == 1


async def test_existing_contact_duplicate_is_handled() -> None:
    store = _Store()
    dedupe_hash = build_dedupe_hash(
        tenant_id=_TENANT,
        email="existing@example.com",
        domain="existing.com",
        company="existing llc",
    )
    assert dedupe_hash is not None
    existing = ContactRecord(
        id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        tenant_id=_TENANT,
        dedupe_hash=dedupe_hash,
        normalized_email="existing@example.com",
        normalized_domain="existing.com",
        normalized_company="existing llc",
        full_name="Existing",
        title=None,
        email="existing@example.com",
        domain="existing.com",
        company_name="Existing LLC",
    )
    store.contacts[(_TENANT, dedupe_hash)] = existing
    service = _service(store)

    result = await _import(
        service,
        csv_text=(
            "name,email,company,domain\n"
            "Existing,existing@example.com,Existing LLC,existing.com\n"
        ),
    )

    assert result.import_record is not None
    assert result.import_record.duplicate_rows == 1
    assert result.rows[0].status == "duplicate"
    assert result.rows[0].contact_id == existing.id


async def test_suppressed_contact_is_not_imported() -> None:
    store = _Store()
    service = _service(store, suppressed_email="blocked@example.com")

    result = await _import(
        service,
        csv_text="name,email,company,domain\nBlocked,blocked@example.com,Acme,acme.com\n",
    )

    assert result.import_record is not None
    assert result.import_record.invalid_rows == 1
    assert result.rows[0].status == "invalid"
    assert "contact_suppressed" in result.rows[0].validation_errors
    assert len(store.contacts) == 0


async def test_csv_import_service_uses_central_rbac_gate() -> None:
    store = _Store()
    service = _service(store)

    with pytest.raises(AppError) as exc:
        await _import(
            service,
            principal=_principal("viewer"),
            csv_text="name,email,company,domain\nJane,jane@example.com,Acme,acme.com\n",
        )

    assert exc.value.code == "FORBIDDEN"
    assert store.imports == {}


async def test_rbac_denied_case_blocks_import_before_storage() -> None:
    store = _Store()
    service = _service(store)

    with pytest.raises(AppError) as exc:
        await _import(
            service,
            principal=_principal("viewer"),
            csv_text="name,email,company,domain\nJane,jane@example.com,Acme,acme.com\n",
        )

    assert exc.value.code == "FORBIDDEN"
    assert store.imports == {}


async def test_billing_gate_denied_case_blocks_import_before_storage() -> None:
    store = _Store()
    service = _service(store, billing_allowed=False)

    with pytest.raises(AppError) as exc:
        await _import(
            service,
            csv_text="name,email,company,domain\nJane,jane@example.com,Acme,acme.com\n",
        )

    assert exc.value.code == "BILLING_FEATURE_DENIED"
    assert store.imports == {}


async def test_idempotency_replay_does_not_create_another_import() -> None:
    store = _Store()
    service = _service(
        store,
        idempotency=_IdempotencyGate(IdempotencyOutcome(IdempotencyState.REPLAY, 201, "hash")),
    )

    result = await _import(
        service,
        csv_text="name,email,company,domain\nJane,jane@example.com,Acme,acme.com\n",
    )

    assert result.idempotency_replay is True
    assert result.import_record is None
    assert store.imports == {}


async def test_no_raw_contact_or_ignored_csv_data_in_audit_details() -> None:
    store = _Store()
    audits: list[dict[str, Any]] = []
    service = _service(store, audits=audits)

    await _import(
        service,
        csv_text="name,email,company,ignored_column\nJane,jane@example.com,Acme,do-not-log\n",
        idempotency_key="safe-key",
    )

    rendered = str(audits).lower()
    assert "jane@example.com" not in rendered
    assert "do-not-log" not in rendered
    assert "ignored_column" not in rendered


def test_cre_import_migration_shape_rls_and_no_later_phase1_workflows() -> None:
    src = (
        Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0011_cre_imports.py"
    ).read_text(encoding="utf-8")

    assert "contact_imports" in src
    assert "contacts" in src
    assert "contact_import_rows" in src
    assert "tenant_id" in src
    assert "idempotency_key" in src
    assert "pending" in src and "processing" in src and "completed" in src and "failed" in src
    assert 'apply_forced_rls("contact_imports")' in src
    assert 'apply_forced_rls("contacts")' in src
    assert 'apply_forced_rls("contact_import_rows")' in src
    lowered = src.lower()
    for forbidden in ("stripe", "twilio", "webhook", "live scraping", "draft", "rag", "research"):
        assert forbidden not in lowered
