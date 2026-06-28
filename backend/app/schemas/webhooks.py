"""Webhook API response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ResendWebhookAcceptedResponse(BaseModel):
    """Safe response returned after Resend webhook verification and normalization."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    status: str
    duplicate: bool = False
    event_type: str | None = None
    mock_only: bool = True


class StripeWebhookAcceptedResponse(BaseModel):
    """Safe response returned after Stripe webhook verification and normalization."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    status: str
    duplicate: bool = False
    event_type: str | None = None
    mock_only: bool = True
