"""Provider webhook endpoints.

P3-5g adds only the Resend verification/normalization foundation. The default
runtime dependency is fail-closed because real secret resolution is not wired in
this slice.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.config import get_settings
from app.schemas.webhooks import ResendWebhookAcceptedResponse, StripeWebhookAcceptedResponse
from app.services.resend_webhooks import (
    InMemoryResendWebhookEventStore,
    ResendWebhookProcessor,
    ResendWebhookVerifier,
)
from app.services.stripe_webhooks import (
    InMemoryStripeWebhookEventStore,
    StripeWebhookProcessor,
    StripeWebhookVerifier,
)

router = APIRouter(tags=["webhooks"])

_RESEND_WEBHOOK_STORE = InMemoryResendWebhookEventStore()
_STRIPE_WEBHOOK_STORE = InMemoryStripeWebhookEventStore()


def stripe_webhook_processor() -> StripeWebhookProcessor:
    settings = get_settings()
    # Real secret resolution from STRIPE_WEBHOOK_SECRET_REF is deferred to a
    # later approved billing smoke slice. Passing no secret keeps the route
    # fail-closed by default in every environment.
    verifier = StripeWebhookVerifier(
        webhook_secret=None,
        secret_ref=settings.stripe_webhook_secret_ref,
    )
    return StripeWebhookProcessor(verifier=verifier, store=_STRIPE_WEBHOOK_STORE)


def resend_webhook_processor() -> ResendWebhookProcessor:
    settings = get_settings()
    # Real secret resolution from EMAIL_PROVIDER_WEBHOOK_SECRET_REF is deferred
    # to the approved secret-management/webhook smoke slice. Passing no secret
    # keeps the route fail-closed by default in every environment.
    verifier = ResendWebhookVerifier(
        webhook_secret=None,
        secret_ref=settings.email_provider_webhook_secret_ref,
    )
    return ResendWebhookProcessor(verifier=verifier, store=_RESEND_WEBHOOK_STORE)


@router.post("/api/v1/webhooks/resend", response_model=ResendWebhookAcceptedResponse)
async def receive_resend_webhook(
    request: Request,
    processor: Annotated[ResendWebhookProcessor, Depends(resend_webhook_processor)],
) -> ResendWebhookAcceptedResponse:
    raw_body = await request.body()
    result = await processor.process(raw_body=raw_body, headers=request.headers)
    return ResendWebhookAcceptedResponse(
        provider=result.provider,
        status=result.status,
        duplicate=result.duplicate,
        event_type=result.event_type,
        mock_only=True,
    )


@router.post("/api/v1/webhooks/stripe", response_model=StripeWebhookAcceptedResponse)
async def receive_stripe_webhook(
    request: Request,
    processor: Annotated[StripeWebhookProcessor, Depends(stripe_webhook_processor)],
) -> StripeWebhookAcceptedResponse:
    raw_body = await request.body()
    result = await processor.process(raw_body=raw_body, headers=request.headers)
    return StripeWebhookAcceptedResponse(
        provider=result.provider,
        status=result.status,
        duplicate=result.duplicate,
        event_type=result.event_type,
        mock_only=True,
    )
