"""Credential service / secret-handling tests (Slice 10). Sentinel fakes only."""

import uuid
from pathlib import Path
from typing import Any

from app.integrations.secrets.backend import LocalSecretBackend
from app.integrations.secrets.kms import LocalKms
from app.services.credentials import CredentialService

_SENTINEL = "sentinel-fake-secret-value"
_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "0004_integration_credentials.py"
)


class _FakeRepo:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    async def insert(self, payload: dict[str, Any]) -> None:
        self.payloads.append(payload)


def test_local_kms_roundtrip_and_ciphertext_differs() -> None:
    kms = LocalKms()
    ct = kms.encrypt(_SENTINEL)
    assert ct != _SENTINEL
    assert kms.decrypt(ct) == _SENTINEL


async def test_store_persists_only_ref_and_metadata() -> None:
    repo = _FakeRepo()
    svc = CredentialService(repo, LocalSecretBackend(), LocalKms())  # type: ignore[arg-type]
    tenant_id = uuid.uuid4()

    stored = await svc.store(
        tenant_id=tenant_id, credential_type="mailbox_password", plaintext=_SENTINEL
    )

    assert stored.secret_ref.startswith("secret://")
    payload = repo.payloads[0]
    # DB row carries only ref + metadata — never the secret.
    assert set(payload.keys()) == {
        "tenant_id",
        "credential_type",
        "secret_ref",
        "envelope_key_id",
        "version",
    }
    assert _SENTINEL not in str(payload)
    assert "plaintext" not in payload


async def test_reveal_is_the_decrypt_path() -> None:
    repo = _FakeRepo()
    backend = LocalSecretBackend()
    svc = CredentialService(repo, backend, LocalKms())  # type: ignore[arg-type]
    tenant_id = uuid.uuid4()
    stored = await svc.store(tenant_id=tenant_id, credential_type="api_key", plaintext=_SENTINEL)

    # Backend holds ciphertext (not plaintext); only reveal() returns plaintext.
    assert backend.get(stored.secret_ref) != _SENTINEL
    assert await svc.reveal(secret_ref=stored.secret_ref) == _SENTINEL


def test_migration_stores_ref_only_with_forced_rls() -> None:
    src = _MIGRATION.read_text(encoding="utf-8")
    assert "secret_ref" in src
    assert 'apply_forced_rls("integration_credentials")' in src
    # No column stores the secret material itself.
    assert 'Column("plaintext"' not in src
    assert 'Column("ciphertext"' not in src
    assert 'Column("secret_value"' not in src
