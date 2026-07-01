"""Repositories for campaigns and campaign-contact selection."""

from __future__ import annotations

import uuid

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping

from app.models.campaign import Campaign, CampaignContact
from app.models.contact import Contact
from app.repositories.base import BaseRepository
from app.services.authz import TenantOwnedObject
from app.services.campaign import CampaignContactRecord, CampaignRecord

_CAMPAIGN_COLUMNS = (
    Campaign.id,
    Campaign.tenant_id,
    Campaign.created_by_user_id,
    Campaign.name,
    Campaign.description,
    Campaign.goal,
    Campaign.target_segment,
    Campaign.notes,
    Campaign.status,
)
_CAMPAIGN_CONTACT_COLUMNS = (
    CampaignContact.id,
    CampaignContact.tenant_id,
    CampaignContact.campaign_id,
    CampaignContact.contact_id,
    CampaignContact.status,
)


def _campaign(row: RowMapping) -> CampaignRecord:
    return CampaignRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        created_by_user_id=row["created_by_user_id"],
        name=row["name"],
        description=row["description"],
        goal=row["goal"],
        target_segment=row["target_segment"],
        notes=row["notes"],
        status=row["status"],
    )


def _campaign_contact(row: RowMapping) -> CampaignContactRecord:
    return CampaignContactRecord(
        id=row["id"],
        tenant_id=row["tenant_id"],
        campaign_id=row["campaign_id"],
        contact_id=row["contact_id"],
        status=row["status"],
    )


class CampaignRepository(BaseRepository):
    async def create_campaign(
        self,
        *,
        tenant_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        name: str,
        description: str | None,
        goal: str | None,
        target_segment: str | None,
        notes: str | None,
        status: str,
    ) -> CampaignRecord:
        row = (
            (
                await self.conn.execute(
                    insert(Campaign)
                    .values(
                        tenant_id=tenant_id,
                        created_by_user_id=created_by_user_id,
                        name=name,
                        description=description,
                        goal=goal,
                        target_segment=target_segment,
                        notes=notes,
                        status=status,
                    )
                    .returning(*_CAMPAIGN_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _campaign(row)

    async def get_campaign(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> CampaignRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_CAMPAIGN_COLUMNS).where(
                        Campaign.tenant_id == tenant_id, Campaign.id == campaign_id
                    )
                )
            )
            .mappings()
            .first()
        )
        return _campaign(row) if row is not None else None

    async def list_campaigns(self, *, tenant_id: uuid.UUID) -> list[CampaignRecord]:
        rows = (
            (
                await self.conn.execute(
                    select(*_CAMPAIGN_COLUMNS)
                    .where(Campaign.tenant_id == tenant_id)
                    .order_by(Campaign.created_at)
                )
            )
            .mappings()
            .all()
        )
        return [_campaign(row) for row in rows]

    async def update_campaign(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        name: str | None,
        description: str | None,
        goal: str | None,
        target_segment: str | None,
        notes: str | None,
        status: str | None,
    ) -> CampaignRecord | None:
        values = {
            key: value
            for key, value in {
                "name": name,
                "description": description,
                "goal": goal,
                "target_segment": target_segment,
                "notes": notes,
                "status": status,
            }.items()
            if value is not None
        }
        if not values:
            return await self.get_campaign(tenant_id=tenant_id, campaign_id=campaign_id)
        row = (
            (
                await self.conn.execute(
                    update(Campaign)
                    .where(Campaign.tenant_id == tenant_id, Campaign.id == campaign_id)
                    .values(**values)
                    .returning(*_CAMPAIGN_COLUMNS)
                )
            )
            .mappings()
            .first()
        )
        return _campaign(row) if row is not None else None

    async def get_contact_object(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> TenantOwnedObject | None:
        row = (
            await self.conn.execute(
                select(Contact.id, Contact.tenant_id).where(
                    Contact.tenant_id == tenant_id,
                    Contact.id == contact_id,
                )
            )
        ).first()
        if row is None:
            return None
        return TenantOwnedObject(id=row.id, tenant_id=row.tenant_id)

    async def get_campaign_contact(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID, contact_id: uuid.UUID
    ) -> CampaignContactRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(*_CAMPAIGN_CONTACT_COLUMNS).where(
                        CampaignContact.tenant_id == tenant_id,
                        CampaignContact.campaign_id == campaign_id,
                        CampaignContact.contact_id == contact_id,
                    )
                )
            )
            .mappings()
            .first()
        )
        return _campaign_contact(row) if row is not None else None

    async def attach_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord:
        row = (
            (
                await self.conn.execute(
                    insert(CampaignContact)
                    .values(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        contact_id=contact_id,
                        status=status,
                    )
                    .returning(*_CAMPAIGN_CONTACT_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _campaign_contact(row)

    async def set_campaign_contact_status(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        contact_id: uuid.UUID,
        status: str,
    ) -> CampaignContactRecord | None:
        row = (
            (
                await self.conn.execute(
                    update(CampaignContact)
                    .where(
                        CampaignContact.tenant_id == tenant_id,
                        CampaignContact.campaign_id == campaign_id,
                        CampaignContact.contact_id == contact_id,
                    )
                    .values(status=status)
                    .returning(*_CAMPAIGN_CONTACT_COLUMNS)
                )
            )
            .mappings()
            .first()
        )
        return _campaign_contact(row) if row is not None else None

    async def list_campaign_contacts(
        self, *, tenant_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> list[CampaignContactRecord]:
        rows = (
            (
                await self.conn.execute(
                    select(*_CAMPAIGN_CONTACT_COLUMNS).where(
                        CampaignContact.tenant_id == tenant_id,
                        CampaignContact.campaign_id == campaign_id,
                    )
                )
            )
            .mappings()
            .all()
        )
        return [_campaign_contact(row) for row in rows]
