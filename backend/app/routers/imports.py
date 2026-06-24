"""Contact CSV import API (Phase 2 P2-1).

Mounts the mature CsvImportService behind ``POST /api/v1/imports/contacts``. The
router validates the request, resolves the authenticated principal, opens a
tenant-scoped DB transaction, and delegates to CsvImportService — which enforces
RBAC, billing, suppression, idempotency, and audit. There are no read/list
paths, no provider calls, and no real sending: those remain deferred.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.audit.repository import AuditRepository
from app.audit.service import AuditService
from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.middleware.error_handler import AppError
from app.repositories.billing_repo import BillingRepository
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.contact_repo import ContactImportRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.schemas.imports import ContactImportRequest, ContactImportResponse
from app.services.authz import RBACService
from app.services.billing import BillingGateService
from app.services.compliance import ComplianceGateService
from app.services.csv_import import CsvImportService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])

IDEMPOTENCY_HEADER = "idempotency-key"


def idempotency_key(request: Request) -> str:
    """Require a non-blank ``Idempotency-Key`` header (risky action — CLAUDE.md rule 7)."""
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required.",
            status_code=400,
        )
    return raw.strip()


async def csv_import_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[CsvImportService]:
    """Build a CsvImportService bound to the caller's tenant-scoped transaction.

    Opens ``app.database.tenant_session`` so every query runs under forced RLS
    with the principal's tenant context, and passes the scoped connection to the
    repositories (which never open their own — CLAUDE.md rule 5). The transaction
    commits when the request succeeds and rolls back if the handler raises.
    """
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        yield CsvImportService(
            store=ContactImportRepository(conn),
            rbac=RBACService(),
            billing=BillingGateService(BillingRepository(conn)),
            compliance=ComplianceGateService(ComplianceRepository(conn)),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            audit_record=audit.record,
        )


@router.post("/contacts", status_code=201)
async def import_contacts(
    body: ContactImportRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[CsvImportService, Depends(csv_import_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> ContactImportResponse:
    """Validate and import a CRE contact CSV. All gates are enforced in the service."""
    try:
        result = await service.import_contacts(
            principal=principal,
            csv_text=body.csv_text,
            source_filename=body.source_filename,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return ContactImportResponse.from_result(result)
