"""Request/response schemas for contact CSV import (POST /api/v1/imports/contacts).

Only safe import metadata is returned — never raw contact rows, emails, domains,
or other PII (CLAUDE.md rule 14). The request carries CSV text; the service
(CsvImportService) owns the authoritative size limit and per-row validation.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.services.csv_import import ContactImportResult

# Coarse request guard only. CsvImportService enforces the authoritative byte
# limit (MAX_CSV_BYTES) and raises CSV_TOO_LARGE.
MAX_CSV_TEXT_CHARS = 1_000_000


class ContactImportRequest(BaseModel):
    """Inbound CSV import payload."""

    csv_text: str = Field(min_length=1, max_length=MAX_CSV_TEXT_CHARS)
    source_filename: str | None = Field(default=None, max_length=255)


class ContactImportSummary(BaseModel):
    """Safe, non-PII summary of an import batch."""

    id: uuid.UUID
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int


class ContactImportResponse(BaseModel):
    """Resource-keyed import result: ``{"import": {...} | null, "idempotency_replay": bool}``."""

    model_config = ConfigDict(populate_by_name=True)

    import_summary: ContactImportSummary | None = Field(default=None, serialization_alias="import")
    idempotency_replay: bool = False

    @classmethod
    def from_result(cls, result: ContactImportResult) -> ContactImportResponse:
        record = result.import_record
        summary = (
            ContactImportSummary(
                id=record.id,
                status=record.status,
                total_rows=record.total_rows,
                valid_rows=record.valid_rows,
                invalid_rows=record.invalid_rows,
                duplicate_rows=record.duplicate_rows,
            )
            if record is not None
            else None
        )
        return cls(import_summary=summary, idempotency_replay=result.idempotency_replay)
