"""Health, liveness, and readiness endpoint tests (Slice 3)."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_live_returns_minimal_liveness() -> None:
    client = TestClient(create_app())
    resp = client.get("/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"
    assert "service" in body


def test_ready_returns_limited_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    client = TestClient(create_app())
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    # DB/migration readiness is wired in Slice 5; until then it is not configured.
    assert body["checks"]["database"] == "not_configured"
