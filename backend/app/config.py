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
    # controlled_demo permits mock providers under APP_ENV=production. It is an
    # owner-gated escape hatch: a blank/placeholder approver makes the boot guard
    # fail closed (see app/observability/boot_guard.py).
    controlled_demo_approved_by: str | None = None

    # Production secrets — shape-checked by the boot guard only; real secret
    # handling (AWS Secrets Manager / KMS) lands in Slice 10.
    jwt_secret: str | None = None
    encryption_key: str | None = None
    webhook_secret: str | None = None

    # Managed auth provider (Clerk). The mock auth path is gated separately on
    # ``app_env != production AND mock_verifier`` (see app/main.py). Issuer /
    # JWKS / audience / authorized-parties are public, non-secret values used by
    # ClerkJwksVerifier; the secret key is shape-checked by the boot guard only
    # and is NEVER read into claims. No real Clerk values are committed (P3-3b).
    auth_provider: str = "managed"  # "managed" (Clerk) in prod; mock path is env-gated
    auth_provider_issuer: str | None = None
    auth_provider_jwks_url: str | None = None  # defaults to {issuer}/.well-known/jwks.json
    auth_provider_audience: str | None = None  # expected `aud` if a JWT template sets it
    auth_provider_authorized_parties: str | None = None  # comma-separated `azp` allowlist
    auth_provider_email_claim: str = "email"
    auth_provider_session_claim: str = "sid"  # noqa: S105 - claim name, not a secret
    auth_provider_mfa_claim: str | None = None  # e.g. a Clerk JWT-template boolean flag
    auth_provider_secret_key: str | None = None  # shape-checked only; real value via secrets mgr
    auth_provider_publishable_key: str | None = None  # public Clerk key; non-placeholder in prod

    # Roles that MUST present a verified MFA factor (owner decision: platform_admin
    # mandatory at launch). enforce_mfa() (app/auth/mfa.py) consumes this. The role
    # is not yet in the RBAC matrix (services/authz.py), so enforcement is inert
    # until it is added — see docs/evidence/phase-3-3b-clerk-verifier-implementation.md.
    auth_mfa_required_roles: str = "platform_admin"

    # Security toggles — must be hardened in production.
    cookie_secure: bool = False
    csrf_enabled: bool = False
    https_only: bool = False
    cors_allow_all: bool = True

    # Secret handling. Production must use AWS Secrets Manager + KMS (Slice 10).
    secret_backend: str = "local"  # noqa: S105 - backend selector, not a secret
    kms_key_id: str | None = None

    # Email provider boundary. P3-5b registers only the network-free mock adapter.
    # Live email sending remains disabled until a later owner-approved provider slice.
    email_provider: str = "mock"
    live_email_sending_enabled: bool = False
    email_provider_secret_ref: str | None = None
    email_provider_webhook_secret_ref: str | None = None
    email_sending_domain: str | None = None

    # Rate-limit foundation. Per-endpoint enforcement is always wired at the route
    # layer; deployments opt in to the baseline per-IP middleware guard. Local/test
    # default stays in-memory. Production must select Redis for multi-worker correctness.
    rate_limit_enabled: bool = False
    rate_limit_default_limit: int = 60
    rate_limit_window_seconds: int = 60
    rate_limit_backend: str = "in_memory"
    rate_limit_redis_url: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_db_configured(self) -> bool:
        return bool(self.database_url)

    @property
    def is_known_env(self) -> bool:
        return self.app_env in _ALLOWED_ENVS


@lru_cache
def get_settings() -> Settings:
    """Return the cached process settings."""
    return Settings()
