"""Router and service tests for Phase 2 P2-8 settings/team/audit APIs."""

import inspect
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.main import create_app
from app.middleware.error_handler import AppError
from app.routers import settings as settings_router
from app.routers.settings import settings_api_service
from app.services.authz import RBACService
from app.services.idempotency import IdempotencyOutcome, IdempotencyState
from app.services.settings_api import (
    AuditEventPage,
    AuditEventReadRecord,
    MembershipReadRecord,
    SettingsAPIService,
    TenantSettingsRecord,
    TenantUpdateResult,
)

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_MEMBER = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_AUDIT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
_HEADERS = {"Idempotency-Key": "settings-key-1"}


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


def _tenant() -> TenantSettingsRecord:
    return TenantSettingsRecord(
        id=_TENANT,
        name="Automated Structure",
        status="active",
        settings={
            "timezone": "Asia/Manila",
            "locale": "en-PH",
            "api_key": "should-not-render",
            "secret_note": "should-not-render",
        },
        created_at=_NOW,
        updated_at=_NOW,
    )


def _membership() -> MembershipReadRecord:
    return MembershipReadRecord(
        id=_MEMBER,
        user_id=_USER,
        role="owner",
        membership_version=3,
        created_at=_NOW,
    )


def _audit_event() -> AuditEventReadRecord:
    return AuditEventReadRecord(
        id=_AUDIT,
        event_type="tenant.settings_updated",
        actor_user_id=_USER,
        object_type="tenant",
        object_id=_TENANT,
        request_id="req_1",
        job_id=None,
        redacted_details={"changed_fields": ["name"], "api_key": "[REDACTED]"},
        created_at=_NOW,
    )


class _FakeSettingsAPIService:
    def __init__(self, *, error: Exception | None = None, replay: bool = False) -> None:
        self.error = error
        self.replay = replay
        self.calls: list[dict[str, Any]] = []

    async def get_current_tenant(self, principal: CurrentPrincipal) -> TenantSettingsRecord:
        self.calls.append({"method": "get_current_tenant", "principal": principal})
        if self.error is not None:
            raise self.error
        return _tenant()

    async def update_current_tenant_idempotent(
        self,
        principal: CurrentPrincipal,
        **kwargs: Any,
    ) -> TenantUpdateResult:
        self.calls.append(
            {"method": "update_current_tenant_idempotent", "principal": principal, **kwargs}
        )
        if self.error is not None:
            raise self.error
        return TenantUpdateResult(tenant=_tenant(), idempotency_replay=self.replay)

    async def list_memberships(
        self, principal: CurrentPrincipal
    ) -> tuple[MembershipReadRecord, ...]:
        self.calls.append({"method": "list_memberships", "principal": principal})
        if self.error is not None:
            raise self.error
        return (_membership(),)

    async def list_audit_events(
        self,
        principal: CurrentPrincipal,
        **kwargs: Any,
    ) -> AuditEventPage:
        self.calls.append({"method": "list_audit_events", "principal": principal, **kwargs})
        if self.error is not None:
            raise self.error
        return AuditEventPage(items=(_audit_event(),), next_cursor=None, limit=kwargs["limit"])


def _client(service: _FakeSettingsAPIService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = _principal
    if service is not None:
        app.dependency_overrides[settings_api_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "json_body", "headers"),
    [
        ("get", "/api/v1/tenants/current", None, None),
        ("patch", "/api/v1/tenants/current", {"name": "New Name"}, _HEADERS),
        ("get", "/api/v1/memberships", None, None),
        ("get", "/api/v1/audit-events", None, None),
    ],
)
def test_settings_routes_require_authentication(
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    headers: dict[str, str] | None,
) -> None:
    resp = TestClient(create_app(), raise_server_exceptions=False).request(
        method, path, json=json_body, headers=headers
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_settings_routes_are_mounted() -> None:
    spec = create_app().openapi()["paths"]
    assert "/api/v1/tenants/current" in spec
    assert "get" in spec["/api/v1/tenants/current"]
    assert "patch" in spec["/api/v1/tenants/current"]
    assert "/api/v1/memberships" in spec
    assert "/api/v1/audit-events" in spec


def test_get_current_tenant_returns_safe_dto() -> None:
    fake = _FakeSettingsAPIService()
    resp = _client(fake).get("/api/v1/tenants/current")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant"]["id"] == str(_TENANT)
    assert body["tenant"]["name"] == "Automated Structure"
    assert body["tenant"]["settings"] == {"timezone": "Asia/Manila", "locale": "en-PH"}
    assert body["mock_only"] is True
    assert "api_key" not in str(body)
    assert "secret" not in str(body).lower()


def test_patch_current_tenant_requires_idempotency_key() -> None:
    fake = _FakeSettingsAPIService()
    resp = _client(fake).patch("/api/v1/tenants/current", json={"name": "New Name"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert fake.calls == []


@pytest.mark.parametrize("field", ["status", "deleted_at", "tenant_id"])
def test_patch_current_tenant_rejects_forbidden_fields(field: str) -> None:
    fake = _FakeSettingsAPIService()
    resp = _client(fake).patch(
        "/api/v1/tenants/current",
        json={field: "not-allowed"},
        headers=_HEADERS,
    )
    assert resp.status_code == 422
    assert fake.calls == []


def test_patch_current_tenant_calls_service_with_safe_body() -> None:
    fake = _FakeSettingsAPIService(replay=True)
    resp = _client(fake).patch(
        "/api/v1/tenants/current",
        json={"name": "New Name", "settings": {"timezone": "UTC"}},
        headers=_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["idempotency_replay"] is True
    call = fake.calls[0]
    assert call["method"] == "update_current_tenant_idempotent"
    assert call["principal"].tenant_id == _TENANT
    assert call["idempotency_key"] == "settings-key-1"
    assert call["name"] == "New Name"
    assert call["settings_patch"] == {"timezone": "UTC"}


def test_memberships_return_safe_tenant_scoped_dtos() -> None:
    fake = _FakeSettingsAPIService()
    resp = _client(fake).get("/api/v1/memberships")
    assert resp.status_code == 200
    body = resp.json()
    assert body["memberships"] == [
        {
            "id": str(_MEMBER),
            "user_id": str(_USER),
            "role": "owner",
            "membership_version": 3,
            "created_at": _NOW.isoformat().replace("+00:00", "Z"),
            "mock_only": True,
        }
    ]
    forbidden = ("provider", "session", "token", "oauth", "secret")
    assert all(term not in str(body).lower() for term in forbidden)


def test_audit_events_return_redacted_details_only_and_are_bounded() -> None:
    fake = _FakeSettingsAPIService()
    resp = _client(fake).get("/api/v1/audit-events?limit=7")
    assert resp.status_code == 200
    body = resp.json()
    event = body["audit_events"][0]
    assert event["event_type"] == "tenant.settings_updated"
    assert event["redacted_details"] == {"changed_fields": ["name"], "api_key": "[REDACTED]"}
    assert "details" not in event
    assert "raw_details" not in event
    assert body["page"]["limit"] == 7
    assert body["mock_only"] is True
    assert fake.calls[0]["limit"] == 7


class _TenantStore:
    def __init__(self, tenant: TenantSettingsRecord | None = None) -> None:
        self.tenant = tenant if tenant is not None else _tenant()
        self.updates: list[dict[str, Any]] = []

    async def get_current_tenant(self) -> TenantSettingsRecord | None:
        return self.tenant

    async def update_current_tenant(
        self, *, name: str | None = None, settings: dict[str, Any] | None = None
    ) -> TenantSettingsRecord:
        assert self.tenant is not None
        self.updates.append({"name": name, "settings": settings})
        self.tenant = TenantSettingsRecord(
            id=self.tenant.id,
            name=name if name is not None else self.tenant.name,
            status=self.tenant.status,
            settings=settings if settings is not None else self.tenant.settings,
            created_at=self.tenant.created_at,
            updated_at=_NOW,
        )
        return self.tenant


class _MembershipStore:
    async def list_memberships(self) -> list[MembershipReadRecord]:
        return [_membership()]


class _AuditStore:
    async def list_recent_bounded(
        self, *, cursor: str | None, limit: int
    ) -> tuple[list[AuditEventReadRecord], str | None]:
        return [_audit_event()], None


class _Idempotency:
    def __init__(self, state: IdempotencyState = IdempotencyState.NEW) -> None:
        self.state = state
        self.completed: list[dict[str, Any]] = []

    async def begin(self, **kwargs: Any) -> IdempotencyOutcome:
        assert kwargs["tenant_id"] == _TENANT
        assert kwargs["actor_user_id"] == _USER
        return IdempotencyOutcome(self.state)

    async def complete(self, **kwargs: Any) -> None:
        self.completed.append(kwargs)


def _service(
    *,
    tenant_store: _TenantStore | None = None,
    idempotency: _Idempotency | None = None,
) -> tuple[SettingsAPIService, _TenantStore, _Idempotency, list[dict[str, Any]]]:
    tenants = tenant_store or _TenantStore()
    idem = idempotency or _Idempotency()
    audits: list[dict[str, Any]] = []

    async def audit_record(**kwargs: Any) -> None:
        audits.append(kwargs)

    return (
        SettingsAPIService(
            tenants=tenants,
            memberships=_MembershipStore(),
            audit_events=_AuditStore(),
            rbac=RBACService(),
            idempotency=idem,
            audit_record=audit_record,
        ),
        tenants,
        idem,
        audits,
    )


@pytest.mark.asyncio
async def test_service_update_requires_team_permission() -> None:
    service, _, _, _ = _service()
    with pytest.raises(AppError) as exc:
        await service.update_current_tenant_idempotent(
            _principal("viewer"),
            idempotency_key="k",
            now=_NOW,
            name="New Name",
        )
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_service_update_rejects_unsafe_settings_key() -> None:
    service, _, _, _ = _service()
    with pytest.raises(AppError) as exc:
        await service.update_current_tenant_idempotent(
            _principal("owner"),
            idempotency_key="k",
            now=_NOW,
            settings_patch={"api_key": "bad"},
        )
    assert exc.value.code == "UNSAFE_TENANT_SETTINGS_FIELD"


@pytest.mark.asyncio
async def test_service_update_audits_changed_field_names_only() -> None:
    service, tenants, idem, audits = _service()
    result = await service.update_current_tenant_idempotent(
        _principal("owner"),
        idempotency_key="k",
        now=_NOW,
        name="New Name",
        settings_patch={"timezone": "UTC"},
    )
    assert result.tenant.name == "New Name"
    assert tenants.updates[0]["settings"] == {"timezone": "UTC", "locale": "en-PH"}
    assert idem.completed
    assert audits[0]["event_type"] == "tenant.settings_updated"
    assert audits[0]["details"] == {"changed_fields": ["name", "settings"]}
    assert "New Name" not in str(audits)
    assert "UTC" not in str(audits)


@pytest.mark.asyncio
async def test_service_audit_events_require_audit_permission() -> None:
    service, _, _, _ = _service()
    with pytest.raises(AppError) as exc:
        await service.list_audit_events(_principal("viewer"), cursor=None, limit=25)
    assert exc.value.code == "FORBIDDEN"


async def test_settings_di_opens_tenant_session_with_principal_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: dict[str, Any] = {}

    class _FakeConn:
        pass

    @asynccontextmanager
    async def fake_tenant_session(
        *, tenant_id: Any, actor_id: Any = None, request_id: Any = None
    ) -> Any:
        opened["tenant_id"] = tenant_id
        opened["actor_id"] = actor_id
        yield _FakeConn()

    monkeypatch.setattr(settings_router, "tenant_session", fake_tenant_session)
    gen = settings_router.settings_api_service(_principal())
    service = await gen.__anext__()
    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, settings_router.SettingsAPIService)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


def test_settings_router_does_not_import_provider_clients() -> None:
    source = inspect.getsource(settings_router).lower()
    forbidden = (
        "clerkmanagement",
        "clerk_client",
        "oauth",
        "stripe",
        "boto3",
        "sendgrid",
        "mailgun",
        "twilio",
    )
    assert all(term not in source for term in forbidden)
