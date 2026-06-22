"""KMS / envelope-encryption interface.

Production uses AWS KMS (real implementation lands during deployment hardening).
Local dev/tests use a reversible encoder that is explicitly NOT real encryption.
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod


class KmsClient(ABC):
    @property
    @abstractmethod
    def key_id(self) -> str: ...

    @abstractmethod
    def encrypt(self, plaintext: str) -> str: ...

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str: ...


class LocalKms(KmsClient):
    """DEV/TEST ONLY. Reversible base64 encoding — NOT cryptographic protection."""

    _PREFIX = "localenc:"

    @property
    def key_id(self) -> str:
        return "local-dev-key"

    def encrypt(self, plaintext: str) -> str:
        return self._PREFIX + base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext.startswith(self._PREFIX):
            raise ValueError("ciphertext was not produced by LocalKms")
        raw = ciphertext[len(self._PREFIX) :]
        return base64.b64decode(raw.encode("ascii")).decode("utf-8")


class AwsKms(KmsClient):
    """Shape only — real AWS KMS calls are implemented during deployment hardening."""

    def __init__(self, key_id: str) -> None:
        self._key_id = key_id

    @property
    def key_id(self) -> str:
        return self._key_id

    def encrypt(self, plaintext: str) -> str:
        raise NotImplementedError("AWS KMS encryption is implemented during deployment hardening")

    def decrypt(self, ciphertext: str) -> str:
        raise NotImplementedError("AWS KMS decryption is implemented during deployment hardening")
