"""Standard error-envelope tests for all error paths (Slice 3)."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import create_app
from app.middleware.error_handler import AppError


def _build_app() -> FastAPI:
    app = create_app()

    @app.get("/_test/app-error")
    async def _app_error() -> dict:
        raise AppError(
            "TEAPOT",
            "I am a teapot.",
            status_code=418,
            details={"hint": "ok", "password": "sekret"},
        )

    @app.get("/_test/http-error")
    async def _http_error() -> dict:
        raise HTTPException(status_code=403, detail="nope")

    @app.get("/_test/boom")
    async def _boom() -> dict:
        raise RuntimeError("explosive internal detail SENTINELSECRET")

    class _Body(BaseModel):
        count: int

    @app.post("/_test/validate")
    async def _validate(body: _Body) -> dict:
        return {"count": body.count}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_app(), raise_server_exceptions=False)


def test_app_error_returns_envelope_and_redacts_details(client: TestClient) -> None:
    resp = client.get("/_test/app-error")
    assert resp.status_code == 418
    body = resp.json()
    assert set(body["error"].keys()) == {"code", "message", "details", "request_id"}
    assert body["error"]["code"] == "TEAPOT"
    assert body["error"]["message"] == "I am a teapot."
    assert body["error"]["request_id"].startswith("req_")
    assert resp.headers["X-Request-ID"].startswith("req_")
    assert body["error"]["details"]["password"] == "***REDACTED***"
    assert body["error"]["details"]["hint"] == "ok"


def test_http_exception_returns_envelope(client: TestClient) -> None:
    resp = client.get("/_test/http-error")
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "PERMISSION_DENIED"
    assert body["error"]["request_id"].startswith("req_")


def test_unknown_path_returns_envelope(client: TestClient) -> None:
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_unexpected_exception_hides_internals(client: TestClient) -> None:
    resp = client.get("/_test/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert body["error"]["request_id"].startswith("req_")
    # Internal details must never leak to the client.
    assert "SENTINELSECRET" not in resp.text
    assert "RuntimeError" not in resp.text


def test_validation_error_drops_input(client: TestClient) -> None:
    resp = client.post("/_test/validate", json={"count": "not-an-int"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    errors = body["error"]["details"]["errors"]
    assert isinstance(errors, list) and errors
    for entry in errors:
        assert set(entry.keys()) <= {"type", "loc", "msg"}
        assert "input" not in entry
