"""Secret backend interface.

Production = AWS Secrets Manager (shape only here). Local dev/tests use an
in-memory backend through the same interface. The backend stores ciphertext
addressed by ``secret_ref``; the database stores only the ref + metadata.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import Settings


class SecretBackend(ABC):
    @abstractmethod
    def put(self, secret_ref: str, ciphertext: str) -> None: ...

    @abstractmethod
    def get(self, secret_ref: str) -> str: ...


class LocalSecretBackend(SecretBackend):
    """DEV/TEST ONLY — in-memory ciphertext store."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def put(self, secret_ref: str, ciphertext: str) -> None:
        self._store[secret_ref] = ciphertext

    def get(self, secret_ref: str) -> str:
        if secret_ref not in self._store:
            raise KeyError("unknown secret_ref")
        return self._store[secret_ref]


class AwsSecretsManagerBackend(SecretBackend):
    """Shape only — real AWS Secrets Manager calls land during deployment hardening."""

    def put(self, secret_ref: str, ciphertext: str) -> None:
        raise NotImplementedError("AWS Secrets Manager is implemented during deployment hardening")

    def get(self, secret_ref: str) -> str:
        raise NotImplementedError("AWS Secrets Manager is implemented during deployment hardening")


def get_secret_backend(settings: Settings) -> SecretBackend:
    if settings.secret_backend == "aws":  # noqa: S105 - backend selector, not a secret
        return AwsSecretsManagerBackend()
    return LocalSecretBackend()
