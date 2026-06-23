"""Repository for safety gate evaluation results."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import insert, select, update

from app.models.safety import SafetyGateResult
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    from app.services.safety import SafetyGateResultRecord


def _safety_gate_result(row: SafetyGateResult) -> SafetyGateResultRecord:
    from app.services.safety import SafetyGateResultRecord

    return SafetyGateResultRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        campaign_id=row.campaign_id,
        contact_id=row.contact_id,
        draft_id=row.draft_id,
        gate_type=row.gate_type,
        status=row.status,
        severity=row.severity,
        reason_code=row.reason_code,
        safe_details=row.safe_details,
        created_at=row.created_at,
    )


class SafetyRepository(BaseRepository):
    async def create_result(
        self,
        *,
        tenant_id: uuid.UUID,
        gate_type: str,
        status: str,
        severity: str,
        reason_code: str,
        safe_details: dict[str, Any],
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> SafetyGateResultRecord:
        row = (
            (
                await self.conn.execute(
                    insert(SafetyGateResult)
                    .values(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        contact_id=contact_id,
                        draft_id=draft_id,
                        gate_type=gate_type,
                        status=status,
                        severity=severity,
                        reason_code=reason_code,
                        safe_details=safe_details,
                    )
                    .returning(SafetyGateResult)
                )
            )
            .scalars()
            .one()
        )
        return _safety_gate_result(row)

    async def get_result(
        self, *, tenant_id: uuid.UUID, result_id: uuid.UUID
    ) -> SafetyGateResultRecord | None:
        row = (
            (
                await self.conn.execute(
                    select(SafetyGateResult).where(
                        SafetyGateResult.tenant_id == tenant_id,
                        SafetyGateResult.id == result_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        return _safety_gate_result(row) if row is not None else None

    async def list_results_for_context(
        self,
        *,
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
    ) -> list[SafetyGateResultRecord]:
        stmt = select(SafetyGateResult).where(SafetyGateResult.tenant_id == tenant_id)
        if campaign_id is not None:
            stmt = stmt.where(SafetyGateResult.campaign_id == campaign_id)
        if contact_id is not None:
            stmt = stmt.where(SafetyGateResult.contact_id == contact_id)
        if draft_id is not None:
            stmt = stmt.where(SafetyGateResult.draft_id == draft_id)

        rows = (await self.conn.execute(stmt)).scalars().all()
        return [_safety_gate_result(r) for r in rows]

    async def update_result_draft_id(
        self, *, tenant_id: uuid.UUID, result_id: uuid.UUID, draft_id: uuid.UUID
    ) -> SafetyGateResultRecord | None:
        row = (
            (
                await self.conn.execute(
                    update(SafetyGateResult)
                    .where(
                        SafetyGateResult.tenant_id == tenant_id,
                        SafetyGateResult.id == result_id,
                    )
                    .values(draft_id=draft_id)
                    .returning(SafetyGateResult)
                )
            )
            .scalars()
            .first()
        )
        return _safety_gate_result(row) if row is not None else None
