"""Credential service — the ONLY approved decrypt path.

Plaintext secrets exist only transiently inside ``store`` and ``reveal``. They
are never persisted to Postgres (only ``secret_ref`` + metadata), never logged,
audited, exported, returned to clients, or placed in error details
(CLAUDE.md §10, rule 14). Callers of ``reveal`` are responsible for not leaking
the returned value.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.integrations.secrets.backend import SecretBackend
from app.integrations.secrets.kms import KmsClient
from app.repositories.credential_repo import CredentialRepository


@dataclass(frozen=True)
class StoredCredential:
    secret_ref: str
    envelope_key_id: str
    version: int
    credential_type: str


class CredentialService:
    def __init__(self, repo: CredentialRepository, backend: SecretBackend, kms: KmsClient) -> None:
        self._repo = repo
        self._backend = backend
        self._kms = kms

    @staticmethod
    def _make_ref(tenant_id: uuid.UUID | str, credential_type: str) -> str:
        return f"secret://{tenant_id}/{credential_type}"

    async def store(
        self, *, tenant_id: uuid.UUID, credential_type: str, plaintext: str
    ) -> StoredCredential:
        """Envelope-encrypt the secret to the backend; persist only ref + metadata."""
        secret_ref = self._make_ref(tenant_id, credential_type)
        ciphertext = self._kms.encrypt(plaintext)
        self._backend.put(secret_ref, ciphertext)
        await self._repo.insert(
            {
                "tenant_id": tenant_id,
                "credential_type": credential_type,
                "secret_ref": secret_ref,
                "envelope_key_id": self._kms.key_id,
                "version": 1,
            }
        )
        return StoredCredential(secret_ref, self._kms.key_id, 1, credential_type)

    async def reveal(self, *, secret_ref: str) -> str:
        """Decrypt and return the plaintext. The only approved decryption point."""
        ciphertext = self._backend.get(secret_ref)
        return self._kms.decrypt(ciphertext)
