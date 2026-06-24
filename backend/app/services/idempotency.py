"""Idempotency service — deterministic replay for retry-safe risky actions.

Protocol (lock precedes any external effect — CLAUDE.md rule 13):

    outcome = await svc.begin(key=..., request_payload=..., now=...)
    if outcome.is_replay:        # same key + same body → return stored result
        return outcome
    if outcome.state is IdempotencyState.IN_PROGRESS:   # concurrent attempt
        # 409 / retry-after: another worker holds the lock
        ...
    # outcome.state is NEW → perform the effect exactly once, then:
    await svc.complete(key=..., response_payload=..., status_code=...)

Key sources: API → ``Idempotency-Key`` header; worker → deterministic job key;
webhook → provider event id. Same key + a *different* body raises
``IdempotencyConflictError`` (code ``IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD``).

Only hashes of request/response are persisted — never raw payloads, and the
conflict error never echoes payload contents (rule 14).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from app.repositories.idempotency_repo import IdempotencyRepository

IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD = "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD"

_DEFAULT_TTL = timedelta(hours=24)
_DEFAULT_LOCK_TTL = timedelta(minutes=5)


def hash_payload(payload: Any) -> str:
    """Stable SHA-256 of a request/response payload (order-insensitive for dicts)."""
    if isinstance(payload, bytes | bytearray):
        data = bytes(payload)
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    else:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    return hashlib.sha256(data).hexdigest()


class IdempotencyState(StrEnum):
    NEW = "new"  # no prior record — caller must perform the effect once.
    IN_PROGRESS = "in_progress"  # a concurrent attempt holds the lock — do not run.
    REPLAY = "replay"  # completed before — return the stored result, do not run.


class IdempotencyConflictError(Exception):
    """Same key reused with a different request payload."""

    code = IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD

    def __init__(self, key: str) -> None:
        # Never include the payloads themselves (rule 14) — only the key identity.
        super().__init__(f"Idempotency key reused with a different payload: {key}")
        self.key = key


@dataclass(frozen=True)
class IdempotencyOutcome:
    state: IdempotencyState
    status_code: int | None = None
    response_hash: str | None = None

    @property
    def is_replay(self) -> bool:
        return self.state is IdempotencyState.REPLAY


class IdempotencyService:
    def __init__(
        self,
        repo: IdempotencyRepository,
        *,
        ttl: timedelta = _DEFAULT_TTL,
        lock_ttl: timedelta = _DEFAULT_LOCK_TTL,
    ) -> None:
        self._repo = repo
        self._ttl = ttl
        self._lock_ttl = lock_ttl

    async def begin(
        self,
        *,
        key: str,
        request_payload: Any,
        now: datetime,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> IdempotencyOutcome:
        """Claim the key (locking it) or report a replay / in-progress / conflict."""
        request_hash = hash_payload(request_payload)
        existing = await self._repo.get(tenant_id=tenant_id, key=key)

        if existing is None:
            await self._repo.insert(
                {
                    "tenant_id": tenant_id,
                    "actor_user_id": actor_user_id,
                    "key": key,
                    "request_hash": request_hash,
                    "locked_until": now + self._lock_ttl,
                    "expires_at": now + self._ttl,
                }
            )
            return IdempotencyOutcome(IdempotencyState.NEW)

        if existing.request_hash != request_hash:
            raise IdempotencyConflictError(key)

        if existing.response_hash is not None:
            return IdempotencyOutcome(
                IdempotencyState.REPLAY, existing.status_code, existing.response_hash
            )

        # Recorded but not yet completed.
        if existing.locked_until is not None and existing.locked_until > now:
            return IdempotencyOutcome(IdempotencyState.IN_PROGRESS)

        # Lock expired without completion → a retry may proceed; re-take the lock.
        await self._repo.relock(tenant_id=tenant_id, key=key, locked_until=now + self._lock_ttl)
        return IdempotencyOutcome(IdempotencyState.NEW)

    async def complete(
        self,
        *,
        key: str,
        response_payload: Any,
        status_code: int,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        """Record the result and release the lock so future calls replay it."""
        await self._repo.mark_completed(
            tenant_id=tenant_id,
            key=key,
            response_hash=hash_payload(response_payload),
            status_code=status_code,
        )
