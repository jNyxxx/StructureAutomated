"""Database config, readiness, and Alembic head tests (Slice 5).

These run without a live database. Migration runtime smoke (alembic upgrade head
against Postgres) runs in CI / a Docker-enabled environment.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.database import check_readiness, code_head_revision
from app.main import create_app


def test_settings_parses_database_url_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app_user:x@localhost:5432/db")
    settings = Settings()
    assert settings.database_url is not None
    assert settings.is_db_configured is True


def test_settings_database_url_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings()
    assert settings.database_url is None
    assert settings.is_db_configured is False


def test_ready_endpoint_without_db_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        resp = client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["checks"]["database"] == "not_configured"
    finally:
        get_settings.cache_clear()


def test_code_head_revision_is_latest() -> None:
    # Exercises the Alembic config + script directory without a database.
    assert code_head_revision() == "0002_core_tenancy"


async def test_readiness_unavailable_does_not_leak_secrets() -> None:
    # Configured but unreachable DB: must report unavailable and never echo the DSN.
    settings = Settings(database_url="postgresql+asyncpg://app_user:SENTINELPW@127.0.0.1:9/nope")
    result = await check_readiness(settings)
    assert result["ready"] is False
    assert result["checks"]["database"] == "unavailable"
    assert "SENTINELPW" not in json.dumps(result)
