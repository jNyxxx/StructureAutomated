"""Mock billing repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping

from app.models.billing import Plan, TenantSubscription
from app.repositories.base import BaseRepository
from app.services.billing import BillingPlan, TenantSubscriptionRecord

_PLAN_COLUMNS = (
    Plan.id,
    Plan.key,
    Plan.name,
    Plan.features,
)
_TENANT_SUBSCRIPTION_COLUMNS = (
    TenantSubscription.tenant_id,
    TenantSubscription.plan_id,
    TenantSubscription.tenant_status,
    TenantSubscription.grace_until,
)


def _plan(row: RowMapping) -> BillingPlan:
    return BillingPlan(
        id=row["id"],
        key=row["key"],
        name=row["name"],
        features=row["features"],
    )


def _record(subscription: RowMapping, plan: RowMapping) -> TenantSubscriptionRecord:
    return TenantSubscriptionRecord(
        tenant_id=subscription["tenant_id"],
        tenant_status=subscription["tenant_status"],
        grace_until=subscription["grace_until"],
        plan=_plan(plan),
    )


class BillingRepository(BaseRepository):
    async def get_subscription(self, tenant_id: uuid.UUID) -> TenantSubscriptionRecord | None:
        stmt = (
            select(
                TenantSubscription.tenant_id.label("tenant_id"),
                TenantSubscription.tenant_status.label("tenant_status"),
                TenantSubscription.grace_until.label("grace_until"),
                Plan.id.label("plan_id"),
                Plan.key.label("plan_key"),
                Plan.name.label("plan_name"),
                Plan.features.label("plan_features"),
            )
            .join(Plan, TenantSubscription.plan_id == Plan.id)
            .where(TenantSubscription.tenant_id == tenant_id)
        )
        row = (await self.conn.execute(stmt)).mappings().first()
        if row is None:
            return None
        return TenantSubscriptionRecord(
            tenant_id=row["tenant_id"],
            tenant_status=row["tenant_status"],
            grace_until=row["grace_until"],
            plan=BillingPlan(
                id=row["plan_id"],
                key=row["plan_key"],
                name=row["plan_name"],
                features=row["plan_features"],
            ),
        )

    async def set_status(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_status: str,
        grace_until: datetime | None,
    ) -> TenantSubscriptionRecord:
        subscription = (
            (
                await self.conn.execute(
                    update(TenantSubscription)
                    .where(TenantSubscription.tenant_id == tenant_id)
                    .values(tenant_status=tenant_status, grace_until=grace_until)
                    .returning(*_TENANT_SUBSCRIPTION_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        plan = (
            (
                await self.conn.execute(
                    select(*_PLAN_COLUMNS).where(Plan.id == subscription["plan_id"])
                )
            )
            .mappings()
            .one()
        )
        return _record(subscription, plan)

    async def create_plan(self, *, key: str, name: str, features: dict[str, bool]) -> BillingPlan:
        row = (
            (
                await self.conn.execute(
                    insert(Plan)
                    .values(key=key, name=name, features=features)
                    .returning(*_PLAN_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        return _plan(row)

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
                    .returning(*_TENANT_SUBSCRIPTION_COLUMNS)
                )
            )
            .mappings()
            .one()
        )
        plan = (
            (await self.conn.execute(select(*_PLAN_COLUMNS).where(Plan.id == plan_id)))
            .mappings()
            .one()
        )
        return _record(subscription, plan)
