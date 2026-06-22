"""Audit service.

Builds and records audit events with secret/PII redaction. ``created_at`` is
never set by the app (the DB sets it). Raw secrets/tokens/credentials never
reach ``redacted_details`` (CLAUDE.md rule 14).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.audit.repository import AuditRepository
from app.observability.logging import redact


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    @staticmethod
    def build_payload(
        *,
        event_type: str,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        object_type: str | None = None,
        object_id: uuid.UUID | None = None,
        request_id: str | None = None,
        job_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # No created_at — the database server sets it.
        return {
            "event_type": event_type,
            "tenant_id": tenant_id,
            "actor_user_id": actor_user_id,
            "object_type": object_type,
            "object_id": object_id,
            "request_id": request_id,
            "job_id": job_id,
            "redacted_details": redact(details or {}),
        }

    async def record(self, **kwargs: Any) -> None:
        await self._repo.insert(self.build_payload(**kwargs))
