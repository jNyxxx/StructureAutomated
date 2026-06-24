"""Safe response schemas for contacts and contact-backed prospects."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.pagination import PageInfo
from app.services.contact_read import ContactReadPage, ContactReadRecord


class ContactDTO(BaseModel):
    """Public contact fields needed by the local/mock frontend table."""

    id: uuid.UUID
    full_name: str | None = None
    title: str | None = None
    email: str | None = None
    domain: str | None = None
    company_name: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: ContactReadRecord) -> ContactDTO:
        return cls(
            id=record.id,
            full_name=record.full_name,
            title=record.title,
            email=record.email,
            domain=record.domain,
            company_name=record.company_name,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ProspectDTO(BaseModel):
    """Prospect projection over contacts until a real prospect table exists."""

    id: uuid.UUID
    contact_id: uuid.UUID
    full_name: str | None = None
    title: str | None = None
    email: str | None = None
    domain: str | None = None
    company_name: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: ContactReadRecord) -> ProspectDTO:
        return cls(
            id=record.id,
            contact_id=record.id,
            full_name=record.full_name,
            title=record.title,
            email=record.email,
            domain=record.domain,
            company_name=record.company_name,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ContactListResponse(BaseModel):
    contacts: list[ContactDTO]
    page: PageInfo

    @classmethod
    def from_page(cls, page: ContactReadPage) -> ContactListResponse:
        return cls(
            contacts=[ContactDTO.from_record(record) for record in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )


class ProspectListResponse(BaseModel):
    prospects: list[ProspectDTO]
    page: PageInfo

    @classmethod
    def from_page(cls, page: ContactReadPage) -> ProspectListResponse:
        return cls(
            prospects=[ProspectDTO.from_record(record) for record in page.items],
            page=PageInfo(next_cursor=page.next_cursor, limit=page.limit),
        )


class ContactDetailResponse(BaseModel):
    contact: ContactDTO

    @classmethod
    def from_record(cls, record: ContactReadRecord) -> ContactDetailResponse:
        return cls(contact=ContactDTO.from_record(record))
