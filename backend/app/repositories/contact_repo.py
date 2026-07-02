"""Repositories for CRE contacts and contact CSV imports."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, insert, or_, select, update
from sqlalchemy.engine import RowMapping

from app.models.contact import Contact, ContactImport, ContactImportRow
from app.repositories.base import BaseRepository
from app.services.contact_read import ContactReadPage, ContactReadRecord
from app.services.csv_import import (
    ContactImportRecord,
    ContactImportRowRecord,
    ContactRecord,
    ParsedContactRow,
)

_CONTACT_COLUMNS = (
    Contact.id,
    Contact.tenant_id,
    Contact.dedupe_hash,
    Contact.normalized_email,
    Contact.normalized_domain,
    Contact.normalized_company,
    Contact.full_name,
    Contact.title,
    Contact.email,
    Contact.domain,
    Contact.company_name,
)
_CONTACT_READ_COLUMNS = (
    Contact.id,
    Contact.tenant_id,
    Contact.full_name,
    Contact.title,
    Contact.email,
    Contact.domain,
    Contact.company_name,
    Contact.created_at,
    Contact.updated_at,
)
_CONTACT_IMPORT_COLUMNS = (
    ContactImport.id,
    ContactImport.tenant_id,
    ContactImport.idempotency_key,
    ContactImport.status,
    ContactImport.total_rows,
    ContactImport.valid_rows,
    ContactImport.invalid_rows,
    ContactImport.duplicate_rows,
)
_CONTACT_IMPORT_ROW_COLUMNS = (
    ContactImportRow.id,
    ContactImportRow.tenant_id,
    ContactImportRow.import_id,
    ContactImportRow.row_number,
    ContactImportRow.row_hash,
    ContactImportRow.status,
    ContactImportRow.validation_errors,
    ContactImportRow.contact_id,
    ContactImportRow.dedupe_hash,
)


def _contact(row: RowMapping) -> ContactRecord:
    return ContactRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        dedupe_hash=row["dedupe_hash"],
        normalized_email=row["normalized_email"],
        normalized_domain=row["normalized_domain"],
        normalized_company=row["normalized_company"],
        full_name=row["full_name"],
        title=row["title"],
        email=row["email"],
        domain=row["domain"],
        company_name=row["company_name"],
    )


def _import(row: RowMapping) -> ContactImportRecord:
    return ContactImportRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        idempotency_key=row["idempotency_key"],
        status=row["status"],
        total_rows=row["total_rows"],
        valid_rows=row["valid_rows"],
        invalid_rows=row["invalid_rows"],
        duplicate_rows=row["duplicate_rows"],
    )


def _import_row(row: RowMapping) -> ContactImportRowRecord:
    return ContactImportRowRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        import_id=row["import_id"],
        row_number=row["row_number"],
        row_hash=row["row_hash"],
        status=row["status"],
        validation_errors=tuple(row["validation_errors"]),
        contact_id=row["contact_id"],
        dedupe_hash=row["dedupe_hash"],
    )


def _contact_read(row: RowMapping) -> ContactReadRecord:
    return ContactReadRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        full_name=row["full_name"],
        title=row["title"],
        email=row["email"],
        domain=row["domain"],
        company_name=row["company_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ContactReadRepository(BaseRepository):
    """Read-only tenant contact repository."""

    async def list_contacts(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> ContactReadPage:
        query = select(*_CONTACT_READ_COLUMNS).where(Contact.tenant_id == tenant_id)
        if cursor is not None:
            try:
                cursor_id = uuid.UUID(cursor)
            except ValueError:
                cursor_id = None
            cursor_contact = None
            if cursor_id is not None:
                cursor_contact = (
                    await self.conn.execute(
                        select(Contact.created_at, Contact.id).where(
                            Contact.tenant_id == tenant_id,
                            Contact.id == cursor_id,
                        )
                    )
                ).first()
            if cursor_contact is None:
                return ContactReadPage(items=(), next_cursor=None, limit=limit)
            query = query.where(
                or_(
                    Contact.created_at < cursor_contact.created_at,
                    and_(
                        Contact.created_at == cursor_contact.created_at,
                        Contact.id < cursor_contact.id,
                    ),
                )
            )

        rows = (
            (
                await self.conn.execute(
                    query.order_by(Contact.created_at.desc(), Contact.id.desc()).limit(limit + 1)
                )
            )
            .mappings()
            .all()
        )
        page_rows = rows[:limit]
        next_cursor = str(page_rows[-1]["id"]) if len(rows) > limit and page_rows else None
        return ContactReadPage(
            items=tuple(_contact_read(row) for row in page_rows),
            next_cursor=next_cursor,
            limit=limit,
        )

    async def get_contact_by_id(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ContactReadRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_CONTACT_READ_COLUMNS).where(
                        Contact.tenant_id == tenant_id, Contact.id == contact_id
                    )
                )
            )
            .mappings()
            .first()
        )
        return _contact_read(row) if row is not None else None


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
                    .returning(*_CONTACT_IMPORT_COLUMNS)
                )
            )
            .mappings()
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
                    .returning(*_CONTACT_IMPORT_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _import(row)

    async def find_contact_by_dedupe_hash(
        self, *, tenant_id: uuid.UUID, dedupe_hash: str
    ) -> ContactRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_CONTACT_COLUMNS).where(
                        Contact.tenant_id == tenant_id,
                        Contact.dedupe_hash == dedupe_hash,
                    )
                )
            )
            .mappings()
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
                    .returning(*_CONTACT_COLUMNS)
                )
            )
            .mappings()
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
                    .returning(*_CONTACT_IMPORT_ROW_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _import_row(created)
