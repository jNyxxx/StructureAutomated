"""Draft generation/read API for Phase 2 P2-3.

No real providers, scraping, sending, send-gate, live jobs, or frontend wiring are
implemented here.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.audit.repository import AuditRepository
from app.audit.service import AuditService
from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.middleware.error_handler import AppError
from app.repositories.billing_repo import BillingRepository
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.contact_repo import ContactReadRepository
from app.repositories.draft_repo import DraftRepository
from app.repositories.idempotency_repo import IdempotencyRepository
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.research_repo import ResearchRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.safety_repo import SafetyRepository
from app.schemas.drafts import (
    DraftDetailResponse,
    DraftEvidenceListResponse,
    DraftGenerateRequest,
    DraftGenerateResponse,
)
from app.schemas.pagination import PageParams
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import BillingGateService
from app.services.compliance import ComplianceGateService
from app.services.draft_generation import DraftGenerationService
from app.services.draft_read import DraftReadService
from app.services.groundedness import GroundednessService
from app.services.idempotency import IdempotencyConflictError, IdempotencyService
from app.services.rag_grounding import RAGGroundingService
from app.services.safety import SafetyService

router = APIRouter(prefix="/api/v1/drafts", tags=["drafts"])

IDEMPOTENCY_HEADER = "idempotency-key"


class _ContactStoreAdapter:
    def __init__(self, repo: ContactReadRepository) -> None:
        self._repo = repo

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        return await self._repo.get_contact_by_id(tenant_id=tenant_id, contact_id=contact_id)


class _DraftResearchStoreAdapter:
    def __init__(
        self, knowledge_repo: KnowledgeRepository, research_repo: ResearchRepository
    ) -> None:
        self._knowledge_repo = knowledge_repo
        self._research_repo = research_repo

    async def get_research_artifact_for_contact(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Any | None:
        return await self._knowledge_repo.get_research_artifact_for_contact(
            tenant_id=tenant_id, contact_id=contact_id
        )

    async def get_artifact(self, *, tenant_id: uuid.UUID, artifact_id: uuid.UUID) -> Any | None:
        return await self._research_repo.get_artifact(tenant_id=tenant_id, artifact_id=artifact_id)


def idempotency_key(request: Request) -> str:
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required.",
            status_code=400,
        )
    return raw.strip()


async def draft_generation_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[DraftGenerationService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        audit = AuditService(AuditRepository(conn))
        billing = BillingGateService(BillingRepository(conn))
        rbac = RBACService()
        object_authz = ObjectAuthorizationService()
        contact_store = _ContactStoreAdapter(ContactReadRepository(conn))
        knowledge_store = KnowledgeRepository(conn)
        research_repo = ResearchRepository(conn)
        research_store = _DraftResearchStoreAdapter(knowledge_store, research_repo)
        safety_store = SafetyRepository(conn)
        compliance = ComplianceGateService(ComplianceRepository(conn), audit.record)
        grounding = RAGGroundingService(
            knowledge_store=knowledge_store,
            campaign_store=CampaignRepository(conn),
            contact_store=contact_store,
            rbac=rbac,
            object_authz=object_authz,
            billing=billing,
            compliance=compliance,
            audit_record=audit.record,
        )
        safety = SafetyService(
            safety_store=safety_store,
            knowledge_store=knowledge_store,
            audit_record=audit.record,
        )
        groundedness = GroundednessService(
            safety_store=safety_store,
            knowledge_store=knowledge_store,
            research_store=research_repo,
            audit_record=audit.record,
        )
        yield DraftGenerationService(
            draft_store=DraftRepository(conn),
            campaign_store=CampaignRepository(conn),
            contact_store=contact_store,
            research_store=research_store,
            grounding_service=grounding,
            rbac=rbac,
            object_authz=object_authz,
            billing=billing,
            safety_service=safety,
            groundedness_service=groundedness,
            compliance=compliance,
            review_store=ReviewRepository(conn),
            idempotency=IdempotencyService(IdempotencyRepository(conn)),
            audit_record=audit.record,
        )


async def draft_read_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[DraftReadService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        yield DraftReadService(
            store=DraftRepository(conn),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
        )


@router.post("/generate", status_code=201, response_model=DraftGenerateResponse)
async def generate_draft(
    body: DraftGenerateRequest,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DraftGenerationService, Depends(draft_generation_service)],
    key: Annotated[str, Depends(idempotency_key)],
) -> DraftGenerateResponse:
    try:
        result = await service.generate_draft(
            principal=principal,
            campaign_id=body.campaign_id,
            contact_id=body.contact_id,
            idempotency_key=key,
            now=datetime.now(UTC),
        )
    except IdempotencyConflictError as exc:
        raise AppError(
            exc.code,
            "Idempotency-Key was reused with a different request.",
            status_code=409,
        ) from exc
    return DraftGenerateResponse.from_result(result)


@router.get("/{draft_id}", response_model=DraftDetailResponse)
async def get_draft(
    draft_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DraftReadService, Depends(draft_read_service)],
) -> DraftDetailResponse:
    draft = await service.get_draft(principal=principal, draft_id=draft_id)
    return DraftDetailResponse.from_record(draft)


@router.get("/{draft_id}/evidence", response_model=DraftEvidenceListResponse)
async def list_draft_evidence(
    draft_id: uuid.UUID,
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[DraftReadService, Depends(draft_read_service)],
) -> DraftEvidenceListResponse:
    evidence_page = await service.list_evidence(
        principal=principal,
        draft_id=draft_id,
        cursor=page.cursor,
        limit=page.limit,
    )
    return DraftEvidenceListResponse.from_page(evidence_page)
