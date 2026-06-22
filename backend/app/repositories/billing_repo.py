"""Mock billing repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import insert, select, update

from app.models.billing import Plan, TenantSubscription
from app.repositories.base import BaseRepository
from app.services.billing import BillingPlan, TenantSubscriptionRecord


def _record(row: TenantSubscription, plan: Plan) -> TenantSubscriptionRecord:
    return TenantSubscriptionRecord(
        tenant_id=row.tenant_id,
        tenant_status=row.tenant_status,
        grace_until=row.grace_until,
        plan=BillingPlan(id=plan.id, key=plan.key, name=plan.name, features=plan.features),
    )


class BillingRepository(BaseRepository):
    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        stmt = (
            select(TenantSubscription, Plan)
            .join(Plan, TenantSubscription.plan_id == Plan.id)
            .where(TenantSubscription.tenant_id == tenant_id)
        )
        row = (await self.conn.execute(stmt)).first()
        if row is None:
            return None
        subscription, plan = row
        return _record(subscription, plan)

    async def set_status(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None,
    ) -> TenantSubscriptionRecord:
        result = await self.conn.execute(
            update(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .values(tenant_status=tenant_status, grace_until=grace_until)
            .returning(TenantSubscription)
        )
        subscription = result.scalars().one()
        plan = (
            (await self.conn.execute(select(Plan).where(Plan.id == subscription.plan_id)))
            .scalars()
            .one()
        )
        return _record(subscription, plan)

    async def create_plan(self, *, key: str, name: str, features: dict[str, bool]) -> BillingPlan:
        plan = (
            (
                await self.conn.execute(
                    insert(Plan).values(key=key, name=name, features=features).returning(Plan)
                )
            )
            .scalars()
            .one()
        )
        return BillingPlan(id=plan.id, key=plan.key, name=plan.name, features=plan.features)

    async def create_subscription(
        self,
        *,
        tenant_id: uuid.UUID,
        plan_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None = None,
    ) -> TenantSubscriptionRecord:
        subscription = (
            (
                await self.conn.execute(
                    insert(TenantSubscription)
                    .values(
                        tenant_id=tenant_id,
                        plan_id=plan_id,
                        tenant_status=tenant_status,
                        grace_until=grace_until,
                    )
                    .returning(TenantSubscription)
                )
            )
            .scalars()
            .one()
        )
        plan = (await self.conn.execute(select(Plan).where(Plan.id == plan_id))).scalars().one()
        return _record(subscription, plan)
