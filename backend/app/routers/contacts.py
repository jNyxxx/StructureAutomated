"""Read-only contacts/prospects API (Phase 2 P2-1b).

Mounts read paths under /api/v1. No contact writes, prospect table, provider
calls, live scraping, sending, webhooks, or frontend changes are introduced.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.database import tenant_session
from app.repositories.contact_repo import ContactReadRepository
from app.schemas.contacts import ContactDetailResponse, ContactListResponse, ProspectListResponse
from app.schemas.pagination import PageParams
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.contact_read import ContactReadService

router = APIRouter(prefix="/api/v1", tags=["contacts"])


async def contact_read_service(
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
) -> AsyncIterator[ContactReadService]:
    """Build the read service inside a tenant-scoped transaction."""
    async with tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id) as conn:
        yield ContactReadService(
            store=ContactReadRepository(conn),
            rbac=RBACService(),
            object_authz=ObjectAuthorizationService(),
        )


@router.get("/prospects", response_model=ProspectListResponse)
async def list_prospects(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ContactReadService, Depends(contact_read_service)],
) -> ProspectListResponse:
    """List contact-backed prospects for the current tenant."""
    result = await service.list_prospects(principal=principal, page=page)
    return ProspectListResponse.from_page(result)


@router.get("/contacts", response_model=ContactListResponse)
async def list_contacts(
    page: Annotated[PageParams, Depends()],
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ContactReadService, Depends(contact_read_service)],
) -> ContactListResponse:
    """List contacts for the current tenant."""
    result = await service.list_contacts(principal=principal, page=page)
    return ContactListResponse.from_page(result)


@router.get("/contacts/{contact_id}", response_model=ContactDetailResponse)
async def get_contact(
    contact_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(current_principal)],
    service: Annotated[ContactReadService, Depends(contact_read_service)],
) -> ContactDetailResponse:
    """Return one tenant-scoped contact."""
    result = await service.get_contact(principal=principal, contact_id=contact_id)
    return ContactDetailResponse.from_record(result)
