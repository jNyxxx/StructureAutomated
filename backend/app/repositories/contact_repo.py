"""Repositories for CRE contacts and contact CSV imports."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import insert, select, update

from app.models.contact import Contact, ContactImport, ContactImportRow
from app.repositories.base import BaseRepository
from app.services.csv_import import (
    ContactImportRecord,
    ContactImportRowRecord,
    ContactRecord,
    ParsedContactRow,
)


def _contact(row: Contact) -> ContactRecord:
    return ContactRecord(
        id=row.id,
        tenant_id=row.tenant_id,
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


def _import(row: ContactImport) -> ContactImportRecord:
    return ContactImportRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        idempotency_key=row.idempotency_key,
        status=row.status,
        total_rows=row.total_rows,
        valid_rows=row.valid_rows,
        invalid_rows=row.invalid_rows,
        duplicate_rows=row.duplicate_rows,
    )


def _import_row(row: ContactImportRow) -> ContactImportRowRecord:
    return ContactImportRowRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        import_id=row.import_id,
        row_number=row.row_number,
        row_hash=row.row_hash,
        status=row.status,
        validation_errors=tuple(row.validation_errors),
        contact_id=row.contact_id,
        dedupe_hash=row.dedupe_hash,
    )


class ContactImportRepository(BaseRepository):
    async def create_import(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        idempotency_key: str,
        source_filename: str | None,
        status: str,
    ) -> ContactImportRecord:
        row = (
            (
                await self.conn.execute(
                    insert(ContactImport)
                    .values(
                        tenant_id=tenant_id,
                        created_by_user_id=actor_user_id,
                        idempotency_key=idempotency_key,
                        source_filename=source_filename,
                        status=status,
                    )
                    .returning(ContactImport)
                )
            )
            .scalars()
            .one()
        )
        return _import(row)

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
        row = (
            (
                await self.conn.execute(
                    update(ContactImport)
                    .where(ContactImport.id == import_id, ContactImport.tenant_id == tenant_id)
                    .values(
                        status=status,
                        total_rows=total_rows,
                        valid_rows=valid_rows,
                        invalid_rows=invalid_rows,
                        duplicate_rows=duplicate_rows,
                        completed_at=completed_at,
                        failed_at=failed_at,
                    )
                    .returning(ContactImport)
                )
            )
            .scalars()
            .one()
        )
        return _import(row)

    async def find_contact_by_dedupe_hash(
        self, *, tenant_id: uuid.UUID, dedupe_hash: str
    ) -> ContactRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(Contact).where(
                        Contact.tenant_id == tenant_id,
                        Contact.dedupe_hash == dedupe_hash,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _contact(row) if row is not None else None

    async def create_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        source_import_id: uuid.UUID,
        row: ParsedContactRow,
    ) -> ContactRecord:
        created = (
            (
                await self.conn.execute(
                    insert(Contact)
                    .values(
                        tenant_id=tenant_id,
                        source_import_id=source_import_id,
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
                    .returning(Contact)
                )
            )
            .scalars()
            .one()
        )
        return _contact(created)

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
        created = (
            (
                await self.conn.execute(
                    insert(ContactImportRow)
                    .values(
                        tenant_id=tenant_id,
                        import_id=import_id,
                        contact_id=contact_id,
                        row_number=row.row_number,
                        row_hash=row.row_hash,
                        dedupe_hash=row.dedupe_hash,
                        status=status,
                        validation_errors=list(validation_errors),
                        normalized_email=row.normalized_email,
                        normalized_domain=row.normalized_domain,
                        normalized_company=row.normalized_company,
                    )
                    .returning(ContactImportRow)
                )
            )
            .scalars()
            .one()
        )
        return _import_row(created)
