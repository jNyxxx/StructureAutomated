# P3-6d — Stripe Webhook Verification Foundation

**Purpose:** Add Stripe webhook signature verification, safe event normalization, idempotency boundary, and a fail-closed route without checkout, Stripe API calls, or money movement.
**Status:** Complete.
**Date:** 2026-06-29 (Asia/Manila)
**Base commit:** `8cb72fa docs(p3-6): record Stripe billing defaults`

---

## 1. Scope and hard stop

P3-6d adds only the Stripe webhook verification foundation.

Confirmed not done:

- no real billing enabled;
- no checkout session creation;
- no billing portal;
- no Stripe API call;
- no Stripe SDK/package;
- no real Stripe credentials;
- no real environment file edit;
- no tenant billing-state mutation from Stripe events;
- no money movement;
- no deployment;
- no AWS provisioning;
- no production enablement;
- no Resend/live sending;
- no SMS or live scraping;
- no billing-gate weakening;
- no auth/RBAC/RLS/tenant-isolation bypass.

---

## 2. Files changed

Code/config:

- `backend/app/services/stripe_webhooks.py`
- `backend/app/routers/webhooks.py`
- `backend/app/schemas/webhooks.py`
- `backend/app/config.py`
- `backend/app/observability/boot_guard.py`
- `.env.example`

Tests:

- `backend/tests/test_stripe_webhooks.py`
- `backend/tests/test_router_stripe_webhooks.py`
- `backend/tests/test_boot_guard.py`

Docs:

- `docs/evidence/phase-3-6d-stripe-webhook-verification-foundation.md`
- `docs/BILLING_STATE_MACHINE.md`
- `docs/API_CONTRACT.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

---

## 3. Verifier behavior

Added:

```text
StripeWebhookVerifier
```

Behavior:

- verifies the raw request body before parsing;
- requires `Stripe-Signature` header;
- parses Stripe-style `t=<timestamp>,v1=<signature>` header parts;
- verifies HMAC-SHA256 over `timestamp.raw_body` using an injected webhook endpoint secret;
- parses JSON only after signature verification succeeds;
- returns safe controlled errors;
- does not log raw body, signature, endpoint secret, customer data, card data, or payment details;
- does not call Stripe;
- does not import Stripe SDK.

Fail-closed behavior:

| Case | Result |
|---|---|
| missing injected webhook secret | `STRIPE_WEBHOOK_SECRET_UNAVAILABLE` / 503 |
| missing `Stripe-Signature` header | `STRIPE_WEBHOOK_SIGNATURE_MISSING` / 401 |
| malformed header without `t` or `v1` | `STRIPE_WEBHOOK_SIGNATURE_MISSING` / 401 |
| invalid signature | `STRIPE_WEBHOOK_SIGNATURE_INVALID` / 401 |
| invalid JSON after verification | `STRIPE_WEBHOOK_PAYLOAD_INVALID` / 400 |

Default route dependency passes no resolved secret because secret resolution is deferred. That keeps the route fail-closed in every environment until an approved billing smoke slice wires real secret resolution.

---

## 4. Event normalization summary

Added:

```text
normalize_stripe_event()
NormalizedStripeWebhookEvent
StripeWebhookProcessingResult
```

Supported normalized event types:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.trial_will_end`
- `charge.refunded`
- `charge.dispute.created`

Unknown event types are ignored safely.

Safe normalized fields only:

- provider;
- provider event id;
- event type;
- occurred timestamp;
- safe object references;
- safe metadata.

Unsafe fields are not returned or persisted:

- raw payload;
- customer email;
- payment method details;
- card data;
- billing address;
- full invoice payload;
- endpoint secret;
- signature value.

---

## 5. Idempotency strategy

Added boundary:

```text
StripeWebhookEventStore.mark_processed(provider_event_id)
```

Added foundation store:

```text
InMemoryStripeWebhookEventStore
```

Behavior:

- first-seen Stripe event id returns `processed`;
- duplicate Stripe event id returns `duplicate`;
- duplicate event ids do not create duplicate processing in this foundation layer.

No migration was added. Durable DB-backed Stripe event persistence remains deferred until approved.

---

## 6. Route behavior

Added route:

```text
POST /api/v1/webhooks/stripe
```

Behavior:

- reads raw request body before parsing;
- verifies signature before event normalization;
- trusts no tenant id from the client body;
- returns only safe response fields;
- default dependency fails closed until secret resolution is implemented;
- does not create checkout sessions;
- does not open billing portal;
- does not call Stripe;
- does not move money;
- does not mutate tenant billing state.

Safe success response shape:

```json
{
  "provider": "stripe",
  "status": "processed",
  "duplicate": false,
  "event_type": "invoice.payment_succeeded",
  "mock_only": true
}
```

---

## 7. Config / boot guard behavior

Added safe config fields:

```text
STRIPE_MODE=test
STRIPE_WEBHOOKS_ENABLED=false
STRIPE_WEBHOOK_SECRET_REF=<placeholder ref>
```

Boot guard behavior:

- production fails closed if Stripe webhooks are enabled and webhook secret ref is missing/placeholder;
- staging fails closed if Stripe webhooks are enabled and webhook secret ref is missing/placeholder;
- `controlled_demo` does not bypass Stripe webhook signing requirements;
- existing billing, Resend, auth, Redis, and RLS boot-guard checks were not weakened.

---

## 8. Tests added / updated

Added:

```text
backend/tests/test_stripe_webhooks.py
backend/tests/test_router_stripe_webhooks.py
```

Updated:

```text
backend/tests/test_boot_guard.py
```

Coverage added:

- missing Stripe webhook secret fails closed;
- missing signature header fails closed;
- invalid signature fails closed;
- valid signed fixture passes verification;
- supported event types normalize correctly;
- unknown events are ignored safely;
- duplicate provider event id is idempotent;
- route is mounted;
- route default dependency fails closed;
- route verifies signature before processing;
- route returns only safe normalized response;
- route does not expose client-supplied tenant id, customer email, or card data;
- service source has no Stripe SDK/API/network markers;
- service source has no tenant billing-state mutation markers;
- production boot guard blocks enabled webhooks without secret ref;
- staging boot guard blocks enabled webhooks without secret ref;
- controlled demo does not bypass webhook signing requirements.

---

## 9. Local verification results

Focused backend checks passed before full gates:

```text
python -m ruff check app tests/test_stripe_webhooks.py tests/test_router_stripe_webhooks.py tests/test_boot_guard.py
python -m black --check app tests/test_stripe_webhooks.py tests/test_router_stripe_webhooks.py tests/test_boot_guard.py
python -m mypy app --ignore-missing-imports
python -m pytest -q tests/test_stripe_webhooks.py tests/test_router_stripe_webhooks.py tests/test_boot_guard.py
```

Full backend result:

```text
ruff PASS
black PASS — 212 files would be left unchanged
mypy PASS — no issues found in 155 source files
pytest PASS — 709 passed, 1 warning in 36.44s
```

Frontend result:

```text
npm ci PASS — 598 packages installed/audited
lint PASS — no ESLint warnings or errors
typecheck PASS
test PASS — 122 passed
build PASS — Next.js 14.2.35 compiled successfully, generated 27 static pages
```

Docker result:

```text
backend Docker build PASS — automatedstructure-backend:p3-6d-local, image 579f8aeb7930, 261MB
frontend Docker build PASS — automatedstructure-frontend:p3-6d-local, image c39f0cb6c1d3, 158MB
```

Known warnings:

- existing FastAPI/Starlette TestClient deprecation warning;
- existing npm audit report: 10 findings;
- existing Vite CJS deprecation warning;
- expected frontend backend-unavailable fallback stderr in tests.

---

## 10. Honest limits

Still not implemented:

- Stripe checkout;
- billing portal;
- Stripe SDK;
- Stripe API calls;
- real Stripe credentials;
- real secret resolution;
- durable Stripe webhook-event persistence;
- tenant billing-state mutation from Stripe events;
- subscription/entitlement sync;
- money movement;
- test-card smoke;
- live billing;
- deployment;
- production enablement.

---

## 11. Final verdict

P3-6d is complete as a Stripe webhook verification, normalization, route, config, boot-guard, and idempotency-boundary foundation.

It does not enable checkout, billing portal, Stripe API calls, real billing, or money movement.
