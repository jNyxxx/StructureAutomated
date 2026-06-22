"""Authenticated request principal.

The principal is created only after the Clerk token is verified, the app user is
resolved through the provider mapping, and membership for the selected tenant is
confirmed. It intentionally carries no raw tokens or secrets.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentPrincipal:
    provider_user_id: str
    provider_session_ref: str
    user_id: uuid.UUID
    email: str
    tenant_id: uuid.UUID
    role: str
    membership_version: int
    mfa_verified: bool
