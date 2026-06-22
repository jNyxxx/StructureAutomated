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

    # Provider mock flags (mocks allowed only in local/dev/demo per the env guard).
    mock_stripe: bool = True
    mock_mailbox: bool = True
    mock_dns: bool = True
    mock_verifier: bool = True
    mock_research: bool = True
    controlled_demo: bool = False

    # Production secrets — shape-checked by the boot guard only; real secret
    # handling (AWS Secrets Manager / KMS) lands in Slice 10.
    jwt_secret: str | None = None
    encryption_key: str | None = None
    webhook_secret: str | None = None

    # Security toggles — must be hardened in production.
    cookie_secure: bool = False
    csrf_enabled: bool = False
    https_only: bool = False
    cors_allow_all: bool = True

    # Secret handling. Production must use AWS Secrets Manager + KMS (Slice 10).
    secret_backend: str = "local"  # noqa: S105 - backend selector, not a secret
    kms_key_id: str | None = None

    # Rate-limit foundation (Slice 12). Off by default — per-endpoint enforcement
    # lands with each route; deployments opt in to the baseline per-IP guard.
    rate_limit_enabled: bool = False
    rate_limit_default_limit: int = 60
    rate_limit_window_seconds: int = 60

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
