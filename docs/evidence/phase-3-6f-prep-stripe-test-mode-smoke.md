# P3-6f-prep — Stripe Internal Test-Mode Smoke Preparation

**Purpose:** Define required concrete values, test-mode gates, internal smoke scenario, hard stop conditions, evidence requirements, and remaining implementation slices before any real Stripe test-mode smoke can run.
**Status:** Complete (prep-only). No Stripe API call, checkout session, billing portal session, billing-state mutation, or money movement.
**Date:** 2026-06-30 (Asia/Manila)
**Base commit:** `2923f57` (P3-7e-dryrun)

---

## 1. Scope and hard stop

This is a preparation document only. It defines what must be true before P3-6g/P3-6h work can proceed.

Confirmed not done in this slice:

- no real Stripe billing enabled;
- no Stripe checkout sessions created;
- no Stripe billing portal sessions created;
- no Stripe API call;
- no Stripe SDK/package added;
- no real Stripe credentials added;
- no real `.env` file edited;
- no live mode enabled;
- no money movement;
- no tenant billing-state mutation from Stripe events;
- no deployment;
- no AWS provisioning;
- no production enabled;
- no Resend/live sending enabled;
- no SMS/live scraping enabled;
- no billing gate weakened;
- no auth/RBAC/RLS/tenant isolation bypassed.

---

## 2. Required concrete values

The following values must be present before any P3-6g/P3-6h work can begin. All secret values must be stored as secret refs — never committed to Git, logs, docs, prompts, audit rows, or client responses.

| Value | What it is | How it must be provided |
|---|---|---|
| `STRIPE_MODE=test` | Stripe API mode | Config; must be `test`, never `live` |
| `STRIPE_WEBHOOKS_ENABLED=true` | Enable webhook route for smoke | Config; explicitly set for smoke env only |
| `STRIPE_WEBHOOK_SECRET_REF` | Non-placeholder path to test webhook signing secret | Secret ref path (not raw value); resolved from Secrets Manager or Stripe CLI |
| `STRIPE_SECRET_KEY_REF` | Non-placeholder path to test-mode Stripe secret key | Secret ref path; resolved value must NOT start with `sk_live_` |
| Named smoke approver | Person who signs off on the smoke run | Owner/operator name + written approval recorded before smoke starts |
| Named emergency-stop operator | Person who can kill the smoke or revoke the test key | Owner/operator name recorded before smoke starts |
| Stripe CLI available | `stripe` CLI installed and authenticated to test-mode Stripe account | Required for event forwarding in P3-6h |

### 2a. Stripe test webhook signing secret

The test webhook signing secret is a `whsec_...` prefixed value. It can be obtained from either:

- Stripe Dashboard → Developers → Webhooks → test mode endpoint → signing secret, OR
- `stripe listen --print-secret` (Stripe CLI test-mode local listener)

It must be stored at the `STRIPE_WEBHOOK_SECRET_REF` path — never committed anywhere as a raw value.

### 2b. Suggested secret ref paths

Staging pattern `/automatedstructure/staging/<service>/<NAME>`:

```text
/automatedstructure/staging/stripe/STRIPE_SECRET_KEY        (test-mode sk_test_...)
/automatedstructure/staging/stripe/STRIPE_WEBHOOK_SECRET    (whsec_... test webhook secret)
```

### 2c. Config block required to unlock the webhook smoke

```env
STRIPE_MODE=test
STRIPE_WEBHOOKS_ENABLED=true
STRIPE_WEBHOOK_SECRET_REF=/automatedstructure/staging/stripe/STRIPE_WEBHOOK_SECRET
STRIPE_SECRET_KEY_REF=/automatedstructure/staging/stripe/STRIPE_SECRET_KEY
STRIPE_CHECKOUT_ENABLED=false
STRIPE_BILLING_PORTAL_ENABLED=false
MOCK_STRIPE=false
```

### 2d. Values NOT required for the webhook smoke

Checkout and portal remain disabled and gated separately until owner approves (P3-6k):

- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
- `STRIPE_PRICE_IDS_REF`
- `STRIPE_PORTAL_RETURN_URL`

These are documented in the P3-6b readiness contract and remain blocked on separate owner approvals.

---

## 3. Required test-mode gates

All of the following must be confirmed before smoke can start.

1. `STRIPE_MODE=test` confirmed in running config — not `live`.
2. `MOCK_STRIPE=false` — smoke uses real test-mode, not mock stub.
3. `STRIPE_CHECKOUT_ENABLED=false` — no checkout sessions during webhook smoke.
4. `STRIPE_BILLING_PORTAL_ENABLED=false` — no portal sessions during webhook smoke.
5. Resolved secret key does NOT start with `sk_live_` — confirmed by the secret resolver before injecting.
6. `STRIPE_WEBHOOK_SECRET_REF` resolves to a non-placeholder `whsec_...` value.
7. Boot guard passes cleanly at `APP_ENV=staging` before smoke starts — no Stripe-related failures in `config_failures()` output.
8. `stripe_billing_readiness_summary()` returns `{test_mode: true, mock_stripe: false}`.
9. Tenant billing-state mutation is NOT wired — `normalize_stripe_event()` result is logged/inspected only; no `tenant_status` update occurs during smoke.
10. No network call to `api.stripe.com` is expected from the backend — signature verification and normalization are local operations; only Stripe CLI makes outbound calls in `stripe listen`.

### 3a. Current code boundary (P3-6d/P3-6e state)

`StripeWebhookVerifier` is constructed with `webhook_secret=None` in `backend/app/routers/webhooks.py`:

```python
verifier = StripeWebhookVerifier(
    webhook_secret=None,
    secret_ref=settings.stripe_webhook_secret_ref,
)
```

Until P3-6g wires in the resolved secret, every `POST /api/v1/webhooks/stripe` request fails closed with `STRIPE_WEBHOOK_VERIFICATION_FAILED` regardless of signature. This is the correct and expected fail-closed behavior.

---

## 4. Internal smoke scenario

The smoke exercises only the webhook verification and normalization path. No checkout sessions, no billing portal sessions, no billing-state mutation.

**Prerequisite:** all §2 concrete values present, all §3 gates confirmed.

| Step | Action | Expected result |
|---|---|---|
| 1 | Confirm `stripe_billing_readiness_summary()` | `{test_mode: true, mock_stripe: false}` |
| 2 | Confirm `GET /ready` returns ok | 200; boot guard + DB + Redis all passing |
| 3 | `POST /api/v1/webhooks/stripe` — no `Stripe-Signature` header | `403` / `STRIPE_WEBHOOK_VERIFICATION_FAILED` |
| 4 | `POST /api/v1/webhooks/stripe` — wrong signature `Stripe-Signature: t=1234,v1=badvalue` | `403` / `STRIPE_WEBHOOK_VERIFICATION_FAILED` |
| 5 | `stripe trigger checkout.session.completed` (Stripe CLI forwarded) | `200 accepted`, `event_type=checkout.session.completed`, `duplicate=false`, `mock_only=true` |
| 6 | `stripe trigger customer.subscription.created` | `200 accepted`, `event_type=customer.subscription.created`, `mock_only=true` |
| 7 | `stripe trigger invoice.payment_succeeded` | `200 accepted`, `event_type=invoice.payment_succeeded`, `mock_only=true` |
| 8 | `stripe trigger invoice.payment_failed` | `200 accepted`, `event_type=invoice.payment_failed`, `mock_only=true` |
| 9 | Resend the same event (same `provider_event_id`) | `200 accepted`, `duplicate=true` |
| 10 | `POST /api/v1/webhooks/stripe` with manually crafted unsupported event type | `200 accepted`, `event_type=null` (normalized to None) |
| 11 | `POST /api/v1/billing/checkout-session` (authenticated) | `503 STRIPE_CHECKOUT_NOT_AVAILABLE` |
| 12 | `POST /api/v1/billing/portal-session` (authenticated) | `503 STRIPE_PORTAL_NOT_AVAILABLE` |
| 13 | Log review | No raw `whsec_...`/`sk_test_...`/`sk_live_...` in logs; no `api.stripe.com` calls from backend; no `tenant_status` DB mutation visible |

### 4a. Stripe CLI forwarding command

```
stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe
```

In a second terminal:

```
stripe trigger checkout.session.completed
stripe trigger customer.subscription.created
stripe trigger invoice.payment_succeeded
stripe trigger invoice.payment_failed
```

### 4b. Alternative: manual HMAC-SHA256 signed payloads

Without Stripe CLI, construct payloads manually. Signature format:

```
Stripe-Signature: t=<unix_ts>,v1=<hex(hmac_sha256(f"{ts}.{payload}", whsec_secret))>
```

See `StripeWebhookVerifier.verify()` in `backend/app/services/stripe_webhooks.py` for the exact implementation.

---

## 5. Hard stop conditions

Abort the smoke immediately and discard evidence if any of the following occur during setup or execution:

1. `STRIPE_MODE=live` detected in the running config.
2. Any resolved secret key starts with `sk_live_` prefix.
3. Any network call to `api.stripe.com` appears in backend logs — the backend must NOT call Stripe directly; only Stripe CLI calls Stripe in the forwarding path.
4. Any Stripe checkout session created (test or live) — the checkout endpoint must return `503`, not a URL.
5. Any Stripe billing portal session created.
6. Any `tenant_status` field mutated in the database from a Stripe webhook event.
7. Any raw Stripe secret value (`whsec_...`, `sk_test_...`, or `sk_live_...`) appears in logs, structured log fields, error detail, HTTP response bodies, or audit rows.
8. Boot guard reports an unexpected Stripe-related failure at startup that implies a live config leaked in.
9. Signature verification passes with no `Stripe-Signature` header or a plainly wrong value — this would indicate the verifier is fail-open (broken).
10. A test event is forwarded to a real or production endpoint instead of the intended smoke target.

---

## 6. Evidence requirements (for P3-6h smoke evidence doc)

`docs/evidence/phase-3-6h-stripe-webhook-smoke.md` must record all of the following:

| Item | What to capture |
|---|---|
| Git commit SHA + image ID | Exact versions of backend image smoked |
| `APP_ENV` | Environment used (`staging` or named local-staging) |
| Stripe mode confirmation | `STRIPE_MODE=test`, not live; confirmed from config or logs |
| Boot guard result | Pass; no Stripe-related failures; `config_failures()` output captured |
| Smoke approver attestation | Named approver + written approval timestamp before smoke started |
| Secret ref paths used | Path names only — never resolved values |
| Webhook fail-closed results (steps 3–4) | HTTP status code + error code for no-sig and wrong-sig cases |
| Per-event-type results (steps 5–8) | `event_type`, `provider_event_id`, `duplicate=false`, `mock_only=true` for each trigger |
| Deduplication result (step 9) | Second send with same `provider_event_id` → `duplicate=true` |
| Unsupported event type result (step 10) | `event_type=null` |
| Billing gate results (steps 11–12) | Checkout → `503` + error code; portal → `503` + error code |
| Log review result | No raw secrets, no `api.stripe.com` calls from backend, no `tenant_status` mutation |
| Named emergency-stop operator | Confirmed name |
| Hard stop conditions | Attestation: none of the §5 conditions triggered |

---

## 7. Remaining implementation slices

| Slice | Goal | Class | Acceptance / stop gate |
|---|---|---|---|
| **P3-6f-prep** | This prep doc — defines values, gates, scenario, evidence, slices | docs-only | This doc committed |
| **P3-6g** | Secret resolution wiring — pass resolved `STRIPE_WEBHOOK_SECRET_REF` to `StripeWebhookVerifier` in `backend/app/routers/webhooks.py`; add readiness summary integration | production readiness | Boot guard passes cleanly with test refs; `stripe_billing_readiness_summary()` returns `config_ready=true`; resolver boundary unit tests |
| **P3-6h** | Internal webhook smoke — Stripe CLI test events forwarded; all §4 scenario steps pass; evidence doc committed | real provider integration (test-mode only) | **STOP GATE.** §2 values present; §3 gates confirmed; §4 smoke complete; §5 hard stops not triggered; §6 evidence doc committed. No billing-state mutation, no checkout/portal session creation. |
| **P3-6i** | Billing state mutation design — define how `customer.subscription.*` events safely update `tenant_status` (idempotency, durable storage, allowlisted transition rules, rollback). Docs-only; owner approval required before implementation. | production readiness (design) | Design approved and recorded; migration plan for durable event storage specified |
| **P3-6j** | Billing state mutation implementation — durable webhook event storage + safe `tenant_status` update from approved Stripe events; only after P3-6i design approved | real provider integration | **STOP GATE.** P3-6i design approved; DB migration exists; idempotency proven in tests; event-to-`tenant_status` update gated by event-type allowlist; no live keys |
| **P3-6k** | Checkout / portal live activation — real session creation enabled only after owner approves self-serve billing with named test price IDs, success/cancel URLs, and portal return URL | real provider integration | **STOP GATE.** Separate owner approval with named price IDs; `stripe_billing_config_failures()` passes; test checkout URL verified; portal URL verified; no live-mode keys until P3-6l approved |

Live-mode approval (P3-6l or equivalent) remains a separate future gate requiring distinct owner attestation, new live Stripe API key refs, and a production deployment approval.

---

## 8. Files created / updated

Created:

- `docs/evidence/phase-3-6f-prep-stripe-test-mode-smoke.md`

Updated:

- `docs/BILLING_STATE_MACHINE.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/STAGING_ENVIRONMENT_TEMPLATE.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

---

## 9. Final verdict

P3-6f-prep is complete. The Stripe test-mode webhook smoke preparation is defined. Required values, gates, scenario, hard stops, evidence contract, and remaining slices P3-6g through P3-6k are documented.

The actual webhook smoke (P3-6h) remains blocked on:

- secret resolution wiring (P3-6g);
- named smoke approver attestation;
- named emergency-stop operator recorded;
- Stripe CLI authenticated to test-mode account.

No Stripe API call, checkout session, billing portal session, billing-state mutation, or money movement was added or enabled in this slice.
