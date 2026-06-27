"""POST /api/v1/imports/contacts router tests (Phase 2 P2-1).

Offline only: CsvImportService and current_principal are overridden with fakes,
so no live DB, auth provider, or real provider calls are exercised. Verifies
auth (401), the Idempotency-Key requirement, the success envelope, service-error
envelope mapping, idempotency replay/conflict, tenant-context wiring, and that
the route is mounted under /api/v1.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import current_principal
from app.auth.principal import CurrentPrincipal
from app.main import create_app
from app.middleware.error_handler import AppError
from app.routers import imports as imports_router
from app.routers.imports import csv_import_service
from app.services.csv_import import ContactImportRecord, ContactImportResult
from app.services.idempotency import IdempotencyConflictError

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

_HEADERS = {"Idempotency-Key": "import-key-1"}
_BODY = {"csv_text": "name,email\nJane,jane@example.com\n", "source_filename": "cre.csv"}


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


class _FakeImportService:
    """Stand-in for CsvImportService that records the call and returns/raises."""

    def __init__(
        self,
        *,
        result: ContactImportResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def import_contacts(self, **kwargs: Any) -> ContactImportResult:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _completed_result() -> ContactImportResult:
    record = ContactImportRecord(
        id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        tenant_id=_TENANT,
        idempotency_key="import-key-1",
        status="completed",
        total_rows=2,
        valid_rows=1,
        invalid_rows=1,
        duplicate_rows=0,
    )
    return ContactImportResult(import_record=record, rows=(), idempotency_replay=False)


def _client(
    service: _FakeImportService | None = None,
    *,
    principal: CurrentPrincipal | None = None,
) -> TestClient:
    app = create_app()
    if principal is not None:
        app.dependency_overrides[current_principal] = lambda: principal
    if service is not None:
        app.dependency_overrides[csv_import_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def test_unauthenticated_request_returns_401() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)

    resp = client.post(
        "/api/v1/imports/contacts",
        json=_BODY,
        headers={"X-Tenant-ID": str(_TENANT), **_HEADERS},
    )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_missing_idempotency_key_returns_400() -> None:
    client = _client(_FakeImportService(result=_completed_result()), principal=_principal())

    resp = client.post("/api/v1/imports/contacts", json=_BODY)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_valid_import_calls_service_with_tenant_context_and_returns_summary() -> None:
    fake = _FakeImportService(result=_completed_result())
    client = _client(fake, principal=_principal())

    resp = client.post("/api/v1/imports/contacts", json=_BODY, headers=_HEADERS)

    assert resp.status_code == 201
    body = resp.json()
    assert body["import"]["status"] == "completed"
    assert body["import"]["total_rows"] == 2
    assert body["import"]["valid_rows"] == 1
    assert body["import"]["invalid_rows"] == 1
    assert body["idempotency_replay"] is False

    call = fake.calls[0]
    assert call["principal"].tenant_id == _TENANT
    assert call["principal"].user_id == _USER
    assert call["idempotency_key"] == "import-key-1"
    assert call["csv_text"] == _BODY["csv_text"]

    # Safe metadata only — no raw contact PII echoed back.
    assert "jane@example.com" not in resp.text


def test_import_contacts_rate_limit_blocks_eleventh_request_per_tenant() -> None:
    fake = _FakeImportService(result=_completed_result())
    client = _client(fake, principal=_principal())

    responses = [
        client.post(
            "/api/v1/imports/contacts",
            json=_BODY,
            headers={"Idempotency-Key": f"import-key-{idx}"},
        )
        for idx in range(11)
    ]

    assert [resp.status_code for resp in responses[:10]] == [201] * 10
    assert responses[10].status_code == 429
    assert responses[10].json()["error"]["code"] == "RATE_LIMITED"
    assert len(fake.calls) == 10


def test_service_app_error_maps_to_standard_envelope() -> None:
    fake = _FakeImportService(
        error=AppError("BILLING_FEATURE_DENIED", "Billing access denied.", status_code=403)
    )
    client = _client(fake, principal=_principal())

    resp = client.post("/api/v1/imports/contacts", json=_BODY, headers=_HEADERS)

    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "BILLING_FEATURE_DENIED"
    assert "request_id" in body["error"]


def test_idempotency_replay_returns_flag_without_summary() -> None:
    fake = _FakeImportService(
        result=ContactImportResult(import_record=None, rows=(), idempotency_replay=True)
    )
    client = _client(fake, principal=_principal())

    resp = client.post("/api/v1/imports/contacts", json=_BODY, headers=_HEADERS)

    assert resp.status_code == 201
    body = resp.json()
    assert body["idempotency_replay"] is True
    assert body["import"] is None


def test_idempotency_conflict_maps_to_409() -> None:
    fake = _FakeImportService(error=IdempotencyConflictError("import-key-1"))
    client = _client(fake, principal=_principal())

    resp = client.post("/api/v1/imports/contacts", json=_BODY, headers=_HEADERS)

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"


def test_import_route_is_mounted_under_api_v1() -> None:
    spec = create_app().openapi()["paths"]

    assert "/api/v1/imports/contacts" in spec
    assert "post" in spec["/api/v1/imports/contacts"]


async def test_di_factory_opens_tenant_session_with_principal_context(
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

    monkeypatch.setattr(imports_router, "tenant_session", fake_tenant_session)

    gen = imports_router.csv_import_service(_principal())
    service = await gen.__anext__()

    assert opened["tenant_id"] == _TENANT
    assert opened["actor_id"] == _USER
    assert isinstance(service, imports_router.CsvImportService)

    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
