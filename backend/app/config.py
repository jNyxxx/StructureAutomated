"""Environment-aware application configuration.

Reads from environment variables (e.g. ``APP_ENV``, ``LOG_LEVEL``). No secrets
are defined here and no ``.env`` file is read by this module — secrets come from
the approved secrets backend in later slices (see CLAUDE.md §10).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_ALLOWED_ENVS = ("local", "development", "staging", "demo", "production")


class Settings(BaseSettings):
    """Process configuration, populated from the environment."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_env: str = "local"
    service_name: str = "backend"
    log_level: str = "INFO"
    database_url: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_db_configured(self) -> bool:
        return self.database_url is not None

    @property
    def is_known_env(self) -> bool:
        return self.app_env in _ALLOWED_ENVS


@lru_cache
def get_settings() -> Settings:
    """Return the cached process settings."""
    return Settings()
