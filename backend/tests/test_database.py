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
        assert body["checks"]["rate_limit_backend"] == "in_memory"
    finally:
        get_settings.cache_clear()


def test_code_head_revision_resolves() -> None:
    # Exercises the Alembic config + script directory without a database.
    head = code_head_revision()
    assert isinstance(head, str) and head.startswith("000")


async def test_readiness_unavailable_does_not_leak_secrets() -> None:
    # Configured but unreachable DB: must report unavailable and never echo the DSN.
    settings = Settings(database_url="postgresql+asyncpg://app_user:SENTINELPW@127.0.0.1:9/nope")
    result = await check_readiness(settings)
    assert result["ready"] is False
    assert result["checks"]["database"] == "unavailable"
    assert "SENTINELPW" not in json.dumps(result)


async def test_readiness_in_memory_rate_limit_does_not_require_redis() -> None:
    settings = Settings(database_url=None, rate_limit_backend="in_memory")

    result = await check_readiness(settings)

    assert result["ready"] is True
    assert result["checks"]["database"] == "not_configured"
    assert result["checks"]["rate_limit_backend"] == "in_memory"
    assert "redis" not in result["checks"]


async def test_readiness_redis_ok_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(url: str) -> bool:
        assert url == "redis://redis:6379/0"
        return True

    monkeypatch.setattr("app.database.check_redis_ready", _ok)
    settings = Settings(
        database_url=None,
        rate_limit_backend="redis",
        rate_limit_redis_url="redis://redis:6379/0",
    )

    result = await check_readiness(settings)

    assert result["ready"] is True
    assert result["checks"]["rate_limit_backend"] == "redis"
    assert result["checks"]["redis"] == "ok"


async def test_readiness_redis_unavailable_is_not_ready_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _down(url: str) -> bool:
        assert "SENTINELPW" in url
        return False

    monkeypatch.setattr("app.database.check_redis_ready", _down)
    settings = Settings(
        database_url=None,
        rate_limit_backend="redis",
        rate_limit_redis_url="redis://user:SENTINELPW@redis:6379/0",
    )

    result = await check_readiness(settings)

    assert result["ready"] is False
    assert result["checks"]["rate_limit_backend"] == "redis"
    assert result["checks"]["redis"] == "unavailable"
    assert "SENTINELPW" not in json.dumps(result)
