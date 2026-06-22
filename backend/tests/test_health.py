"""Health, liveness, and readiness endpoint tests (Slice 3)."""

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_health_returns_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_live_returns_minimal_liveness() -> None:
    resp = client.get("/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"
    assert "service" in body


def test_ready_returns_limited_readiness() -> None:
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    # DB/migration readiness is wired in Slice 5; until then it is not configured.
    assert body["checks"]["database"] == "not_configured"
