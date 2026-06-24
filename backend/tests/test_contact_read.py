"""ContactReadService tests for Phase 2 P2-1b."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.auth.principal import CurrentPrincipal
from app.middleware.error_handler import AppError
from app.schemas.pagination import MAX_PAGE_LIMIT, PageParams
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.contact_read import ContactReadPage, ContactReadRecord, ContactReadService

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CONTACT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_OTHER_CONTACT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)


def _principal(role: str = "owner") -> CurrentPrincipal:
    return CurrentPrincipal(
        provider_user_id="user_clerk_1",
        provider_session_ref="sess_safe_ref",
        user_id=_USER,
        email="owner@example.com",
        tenant_id=_TENANT,
        role=role,
        membership_version=1,
        mfa_verified=True,
    )


def _record(
    *, contact_id: uuid.UUID = _CONTACT, tenant_id: uuid.UUID = _TENANT
) -> ContactReadRecord:
    return ContactReadRecord(
        id=contact_id,
        tenant_id=tenant_id,
        full_name="Jane Owner",
        title="Founder",
        email="jane@example.com",
        domain="example.com",
        company_name="Example CRE",
        created_at=_NOW,
        updated_at=_NOW,
    )


class _Store:
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, ContactReadRecord] = {_CONTACT: _record()}
        self.last_list_call: dict[str, Any] | None = None
        self.write_called = False

    async def list_contacts(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> ContactReadPage:
        self.last_list_call = {"tenant_id": tenant_id, "cursor": cursor, "limit": limit}
        items = tuple(row for row in self.rows.values() if row.tenant_id == tenant_id)
        return ContactReadPage(items=items[:limit], next_cursor="next-contact", limit=limit)

    async def get_contact_by_id(
        self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ContactReadRecord | None:
        row = self.rows.get(contact_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return row

    async def write_marker(self, **_: Any) -> None:
        self.write_called = True


def _service(store: _Store | None = None) -> ContactReadService:
    return ContactReadService(
        store=store or _Store(),
        rbac=RBACService(),
        object_authz=ObjectAuthorizationService(),
    )


@pytest.mark.parametrize("role", ["owner", "admin", "marketer", "viewer"])
async def test_roles_with_dashboard_read_can_list_contacts(role: str) -> None:
    store = _Store()
    result = await _service(store).list_contacts(principal=_principal(role), page=PageParams())

    assert len(result.items) == 1
    assert result.items[0].id == _CONTACT
    assert store.last_list_call == {"tenant_id": _TENANT, "cursor": None, "limit": 25}
    assert store.write_called is False


@pytest.mark.parametrize("role", ["reviewer", "billing_admin", "unknown"])
async def test_roles_without_dashboard_read_are_denied(role: str) -> None:
    with pytest.raises(AppError) as exc:
        await _service().list_contacts(principal=_principal(role), page=PageParams())

    assert exc.value.status_code == 403
    assert exc.value.code == "FORBIDDEN"


async def test_get_contact_returns_same_tenant_contact() -> None:
    store = _Store()
    result = await _service(store).get_contact(principal=_principal(), contact_id=_CONTACT)

    assert result.id == _CONTACT
    assert result.tenant_id == _TENANT
    assert store.write_called is False


@pytest.mark.parametrize("contact_id", [_OTHER_CONTACT, _CONTACT])
async def test_missing_or_cross_tenant_contact_returns_object_denied(contact_id: uuid.UUID) -> None:
    store = _Store()
    if contact_id == _CONTACT:
        store.rows[_CONTACT] = _record(contact_id=_CONTACT, tenant_id=_OTHER_TENANT)

    with pytest.raises(AppError) as exc:
        await _service(store).get_contact(principal=_principal(), contact_id=contact_id)

    assert exc.value.status_code == 403
    assert exc.value.code == "OBJECT_ACCESS_DENIED"


async def test_prospects_projection_uses_contacts_safely() -> None:
    store = _Store()
    result = await _service(store).list_prospects(principal=_principal(), page=PageParams())

    assert len(result.items) == 1
    assert result.items[0].id == _CONTACT
    assert store.last_list_call == {"tenant_id": _TENANT, "cursor": None, "limit": 25}
    assert store.write_called is False


async def test_pagination_clamp_is_preserved_by_service_call() -> None:
    store = _Store()
    page = PageParams(limit=10_000, cursor="cursor-1")

    result = await _service(store).list_contacts(principal=_principal(), page=page)

    assert page.limit == MAX_PAGE_LIMIT
    assert result.limit == MAX_PAGE_LIMIT
    assert store.last_list_call == {"tenant_id": _TENANT, "cursor": "cursor-1", "limit": 100}
