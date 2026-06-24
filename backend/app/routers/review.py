"""Read-only review queue API for Phase 2 P2-3.

Review approve/reject/regenerate, send-gate, sending, providers, and frontend
wiring remain deferred.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.repositories.review_repo import ReviewRepository
from app.schemas.pagination import PageParams
from app.schemas.review import ReviewItemDetailResponse, ReviewItemListResponse
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.review_read import ReviewReadService

router = APIRouter(prefix="/api/v1/review/items", tags=["review"])


async def review_read_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[ReviewReadService]:
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        yield ReviewReadService(
            store=ReviewRepository(conn),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
        )


@router.get("", response_model=ReviewItemListResponse)
async def list_review_items(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ReviewReadService, Depends(review_read_service)],
    campaign_id: uuid.UUID | None = None,
    status: str | None = None,
) -> ReviewItemListResponse:
    items = await service.list_items(
        principal=principal,
        cursor=page.cursor,
        limit=page.limit,
        campaign_id=campaign_id,
        status=status,
    )
    return ReviewItemListResponse.from_page(items)


@router.get("/{review_id}", response_model=ReviewItemDetailResponse)
async def get_review_item(
    review_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ReviewReadService, Depends(review_read_service)],
) -> ReviewItemDetailResponse:
    item = await service.get_item(principal=principal, review_id=review_id)
    return ReviewItemDetailResponse.from_record(item)
