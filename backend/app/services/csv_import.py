"""CSV contact import foundation for Phase 1 Slice P1-01.

This module parses and validates CRE contact CSVs only. It deliberately does not
implement campaigns, research, RAG, draft generation, review, sending,
follow-ups, dashboards, live scraping, or provider integrations.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.services.authz import CAN_IMPORT_CONTACTS, RBACService
from app.services.billing import CAN_CREATE_CAMPAIGN, BillingGateService
from app.services.compliance import EMAIL, ComplianceGateService
from app.services.idempotency import IdempotencyOutcome, IdempotencyState

MAX_CSV_BYTES = 1_000_000
IMPORT_BILLING_GATE = CAN_CREATE_CAMPAIGN
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DOMAIN_RE = re.compile(r"^[a-z0-9.-]+\.[a-z]{2,}$")


class ContactImportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContactImportRowStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    DUPLICATE = "duplicate"
    IMPORTED = "imported"


@dataclass(frozen=True)
class ParsedContactRow:
    row_number: int
    row_hash: str
    full_name: str | None
    title: str | None
    email: str | None
    domain: str | None
    company_name: str | None
    normalized_email: str | None
    normalized_domain: str | None
    normalized_company: str | None
    dedupe_hash: str | None
    validation_errors: tuple[str, ...]


@dataclass(frozen=True)
class ContactRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    dedupe_hash: str
    normalized_email: str | None
    normalized_domain: str | None
    normalized_company: str | None
    full_name: str | None
    title: str | None
    email: str | None
    domain: str | None
    company_name: str | None


@dataclass(frozen=True)
class ContactImportRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    idempotency_key: str
    status: str
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0


@dataclass(frozen=True)
class ContactImportRowRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    import_id: uuid.UUID
    row_number: int
    row_hash: str
    status: str
    validation_errors: tuple[str, ...]
    contact_id: uuid.UUID | None = None
    dedupe_hash: str | None = None


@dataclass(frozen=True)
class ContactImportResult:
    import_record: ContactImportRecord | None
    rows: tuple[ContactImportRowRecord, ...]
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


class ContactImportStore(Protocol):
    async def create_import(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        idempotency_key: str,
        source_filename: str | None,
        status: str,
    ) -> ContactImportRecord:
        """Create an import batch."""

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
        """Update import counts/status."""

    async def find_contact_by_dedupe_hash(
        self, *, tenant_id: uuid.UUID, dedupe_hash: str
    ) -> ContactRecord | None:
        """Return an existing tenant contact by minimized dedupe hash."""

    async def create_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        source_import_id: uuid.UUID,
        row: ParsedContactRow,
    ) -> ContactRecord:
        """Create a tenant contact from a validated row."""

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
        """Persist row-level validation/import result."""


AuditRecorder = Callable[..., Awaitable[None]]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _field(row: dict[str, str], *names: str) -> str | None:
    lowered = {k.strip().lower(): v for k, v in row.items() if k is not None}
    for name in names:
        value = lowered.get(name)
        if value is not None:
            return _clean(value)
    return None


def normalize_email(value: str | None) -> str | None:
    cleaned = _clean(value)
    return cleaned.lower() if cleaned is not None else None


def normalize_domain(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    lowered = cleaned.lower().removeprefix("https://").removeprefix("http://")
    lowered = lowered.removeprefix("www.").split("/")[0].strip()
    return lowered or None


def normalize_company(value: str | None) -> str | None:
    cleaned = _clean(value)
    return " ".join(cleaned.lower().split()) if cleaned is not None else None


def _hash_payload(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_dedupe_hash(
    *, tenant_id: uuid.UUID, email: str | None, domain: str | None, company: str | None
) -> str | None:
    if email is not None:
        basis = f"email:{email}"
    elif domain is not None and company is not None:
        basis = f"domain_company:{domain}:{company}"
    elif company is not None:
        basis = f"company:{company}"
    else:
        return None
    return _hash_payload(f"{tenant_id}:{basis}")


def parse_contact_csv(csv_text: str, *, tenant_id: uuid.UUID) -> tuple[ParsedContactRow, ...]:
    if len(csv_text.encode("utf-8")) > MAX_CSV_BYTES:
        raise AppError("CSV_TOO_LARGE", "CSV file is too large.", status_code=400)
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise AppError("CSV_HEADERS_REQUIRED", "CSV headers are required.", status_code=400)

    parsed: list[ParsedContactRow] = []
    for row_number, raw in enumerate(reader, start=2):
        full_name = _field(raw, "full_name", "name", "contact_name")
        title = _field(raw, "title", "job_title", "role")
        email = _field(raw, "email", "email_address", "work_email")
        domain = _field(raw, "domain", "company_domain", "website")
        company_name = _field(raw, "company", "company_name", "account", "organization")
        normalized_email = normalize_email(email)
        normalized_domain = normalize_domain(domain)
        normalized_company = normalize_company(company_name)
        errors: list[str] = []

        if normalized_email is not None and _EMAIL_RE.match(normalized_email) is None:
            errors.append("invalid_email")
        if normalized_domain is not None and _DOMAIN_RE.match(normalized_domain) is None:
            errors.append("invalid_domain")
        if normalized_email is None and normalized_domain is None and normalized_company is None:
            errors.append("missing_contact_identity")

        dedupe_hash = build_dedupe_hash(
            tenant_id=tenant_id,
            email=normalized_email if "invalid_email" not in errors else None,
            domain=normalized_domain if "invalid_domain" not in errors else None,
            company=normalized_company,
        )
        raw_basis = "|".join(
            [
                str(row_number),
                normalized_email or "",
                normalized_domain or "",
                normalized_company or "",
                full_name or "",
                title or "",
            ]
        )
        parsed.append(
            ParsedContactRow(
                row_number=row_number,
                row_hash=_hash_payload(raw_basis),
                full_name=full_name,
                title=title,
                email=normalized_email,
                domain=normalized_domain,
                company_name=company_name,
                normalized_email=normalized_email,
                normalized_domain=normalized_domain,
                normalized_company=normalized_company,
                dedupe_hash=dedupe_hash,
                validation_errors=tuple(errors),
            )
        )
    return tuple(parsed)


class CsvImportService:
    """Validates/imports contacts under central Phase 0 gates.

    Billing uses ``can_create_campaign`` because Phase 0 has no import-specific
    billing feature yet and imports are only useful as a precursor to campaign
    creation. This keeps import creation behind the safest existing costly-action
    gate until a dedicated import feature is added.
    """

    def __init__(
        self,
        *,
        store: ContactImportStore,
        rbac: RBACService,
        billing: BillingGateService,
        compliance: ComplianceGateService,
        idempotency: IdempotencyGate | None = None,
        audit_record: AuditRecorder | None = None,
    ) -> None:
        self._store = store
        self._rbac = rbac
        self._billing = billing
        self._compliance = compliance
        self._idempotency = idempotency
        self._audit_record = audit_record

    async def import_contacts(
        self,
        *,
        principal: CurrentPrincipal,
        csv_text: str,
        source_filename: str | None,
        idempotency_key: str,
        now: datetime,
    ) -> ContactImportResult:
        self._rbac.require(principal, CAN_IMPORT_CONTACTS)
        await self._billing.require_feature(principal.tenant_id, IMPORT_BILLING_GATE, now=now)

        request_payload = {
            "tenant_id": str(principal.tenant_id),
            "source_filename_present": source_filename is not None,
            "csv_hash": _hash_payload(csv_text),
        }
        if self._idempotency is not None:
            outcome = await self._idempotency.begin(
                key=idempotency_key,
                request_payload=request_payload,
                now=now,
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
            )
            if outcome.state is IdempotencyState.REPLAY:
                return ContactImportResult(import_record=None, rows=(), idempotency_replay=True)
            if outcome.state is IdempotencyState.IN_PROGRESS:
                raise AppError(
                    "IMPORT_IN_PROGRESS", "Import is already in progress.", status_code=409
                )

        parsed_rows = parse_contact_csv(csv_text, tenant_id=principal.tenant_id)
        import_record = await self._store.create_import(
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
            source_filename=source_filename,
            status=ContactImportStatus.PROCESSING.value,
        )
        await self._audit(
            event_type="contact_import.created",
            tenant_id=principal.tenant_id,
            actor_user_id=principal.user_id,
            object_id=import_record.id,
            details={"status": ContactImportStatus.PROCESSING.value, "rows": len(parsed_rows)},
        )

        rows: list[ContactImportRowRecord] = []
        seen_hashes: set[str] = set()
        valid_count = 0
        invalid_count = 0
        duplicate_count = 0

        try:
            for parsed in parsed_rows:
                errors = list(parsed.validation_errors)
                contact_id: uuid.UUID | None = None
                status = ContactImportRowStatus.IMPORTED.value

                if parsed.dedupe_hash is None:
                    errors.append("missing_dedupe_key")
                if parsed.dedupe_hash is not None and parsed.dedupe_hash in seen_hashes:
                    status = ContactImportRowStatus.DUPLICATE.value
                elif parsed.dedupe_hash is not None:
                    seen_hashes.add(parsed.dedupe_hash)

                if parsed.email is not None and await self._compliance.is_suppressed(
                    tenant_id=principal.tenant_id,
                    channel=EMAIL,
                    contact_identifier=parsed.email,
                ):
                    errors.append("contact_suppressed")

                if errors:
                    status = ContactImportRowStatus.INVALID.value
                elif (
                    status != ContactImportRowStatus.DUPLICATE.value
                    and parsed.dedupe_hash is not None
                ):
                    existing = await self._store.find_contact_by_dedupe_hash(
                        tenant_id=principal.tenant_id, dedupe_hash=parsed.dedupe_hash
                    )
                    if existing is not None:
                        status = ContactImportRowStatus.DUPLICATE.value
                        contact_id = existing.id
                    else:
                        contact = await self._store.create_contact(
                            tenant_id=principal.tenant_id,
                            source_import_id=import_record.id,
                            row=parsed,
                        )
                        contact_id = contact.id

                if status == ContactImportRowStatus.IMPORTED.value:
                    valid_count += 1
                elif status == ContactImportRowStatus.INVALID.value:
                    invalid_count += 1
                elif status == ContactImportRowStatus.DUPLICATE.value:
                    duplicate_count += 1

                rows.append(
                    await self._store.create_import_row(
                        tenant_id=principal.tenant_id,
                        import_id=import_record.id,
                        row=parsed,
                        status=status,
                        validation_errors=tuple(errors),
                        contact_id=contact_id,
                    )
                )

            completed = await self._store.update_import_status(
                import_id=import_record.id,
                tenant_id=principal.tenant_id,
                status=ContactImportStatus.COMPLETED.value,
                total_rows=len(parsed_rows),
                valid_rows=valid_count,
                invalid_rows=invalid_count,
                duplicate_rows=duplicate_count,
                completed_at=now,
                failed_at=None,
            )
            await self._audit(
                event_type="contact_import.completed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_id=import_record.id,
                details={
                    "status": ContactImportStatus.COMPLETED.value,
                    "total_rows": len(parsed_rows),
                    "valid_rows": valid_count,
                    "invalid_rows": invalid_count,
                    "duplicate_rows": duplicate_count,
                },
            )
            if self._idempotency is not None:
                await self._idempotency.complete(
                    key=idempotency_key,
                    response_payload={
                        "import_id": str(import_record.id),
                        "total_rows": len(parsed_rows),
                        "valid_rows": valid_count,
                        "invalid_rows": invalid_count,
                        "duplicate_rows": duplicate_count,
                    },
                    status_code=201,
                    tenant_id=principal.tenant_id,
                )
            return ContactImportResult(import_record=completed, rows=tuple(rows))
        except Exception:
            await self._store.update_import_status(
                import_id=import_record.id,
                tenant_id=principal.tenant_id,
                status=ContactImportStatus.FAILED.value,
                total_rows=len(parsed_rows),
                valid_rows=valid_count,
                invalid_rows=invalid_count,
                duplicate_rows=duplicate_count,
                completed_at=None,
                failed_at=now,
            )
            await self._audit(
                event_type="contact_import.failed",
                tenant_id=principal.tenant_id,
                actor_user_id=principal.user_id,
                object_id=import_record.id,
                details={"status": ContactImportStatus.FAILED.value, "rows": len(parsed_rows)},
            )
            raise

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
            object_type="contact_import",
            object_id=object_id,
            details=details,
        )
