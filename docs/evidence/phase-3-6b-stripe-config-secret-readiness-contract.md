# P3-6b — Stripe Config / Secret Readiness Contract

**Purpose:** Define the Stripe config, secret-ref, URL, product/price, webhook-readiness, and billing-readiness contract before any Stripe implementation.
**Status:** Docs-only readiness contract complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `6768a81 docs(p3-6): add Stripe billing owner decision packet`

---

## 1. Scope and hard stop

P3-6b is documentation only.

Confirmed not done:

- no Stripe implementation;
- no Stripe SDK/package;
- no Stripe credentials;
- no Stripe API call;
- no checkout;
- no webhook implementation;
- no billing portal;
- no real billing enablement;
- no money movement;
- no real environment file edit;
- no deployment;
- no AWS provisioning;
- no production enablement;
- no Resend/live sending;
- no SMS;
- no live scraping;
- no billing-gate weakening;
- no auth/RBAC/RLS/tenant-isolation bypass.

Current billing remains mock-only. `MOCK_STRIPE=true` remains the safe default.

---

## 2. Required Stripe secret refs

Future Stripe implementation must use config references only. Raw values must never be committed, logged, returned, stored in database rows, added to frontend config, inserted in audit payloads, pasted into prompts, or placed in evidence.

Required refs:

| Ref | Required before | Notes |
|---|---|---|
| `STRIPE_SECRET_KEY_REF` | Any test-mode API call | Server-only ref. Raw value resolved only inside approved backend secret resolver. |
| `STRIPE_WEBHOOK_SECRET_REF` | Any webhook verification | Server-only ref. Required before trusting webhook payloads. |
| `STRIPE_PRICE_ID_*` refs | Checkout/subscription creation | One reviewed mapping per plan/interval. |
| `STRIPE_BILLING_PORTAL_CONFIG_REF` | Billing portal, if enabled | Optional until portal is approved. |

Recommended staging naming convention:

```text
/automatedstructure/staging/billing/STRIPE_SECRET_KEY
/automatedstructure/staging/billing/STRIPE_WEBHOOK_SECRET
/automatedstructure/staging/billing/STRIPE_PRICE_<PLAN>_<INTERVAL>
/automatedstructure/staging/billing/STRIPE_BILLING_PORTAL_CONFIG
```

Recommended production naming convention:

```text
/automatedstructure/production/billing/STRIPE_SECRET_KEY
/automatedstructure/production/billing/STRIPE_WEBHOOK_SECRET
/automatedstructure/production/billing/STRIPE_PRICE_<PLAN>_<INTERVAL>
/automatedstructure/production/billing/STRIPE_BILLING_PORTAL_CONFIG
```

Rules:

- refs must be non-placeholder;
- refs must be environment-specific;
- staging refs must never point at production live values;
- live refs must not exist in committed files;
- frontend may receive only publishable/non-sensitive values if a future slice approves them;
- server credentials must stay server-only.

---

## 3. Required URLs

Required URL values before checkout/portal/webhook implementation:

| URL | Required before | Notes |
|---|---|---|
| Checkout success URL | Checkout skeleton | Must be environment-specific. |
| Checkout cancel URL | Checkout skeleton | Must be environment-specific. |
| Billing portal return URL | Portal skeleton | Required only if portal is enabled. |
| Stripe webhook endpoint URL | Webhook setup | Must be HTTPS outside local/dev. |

Staging and production URLs must be separate.

Example ref labels only:

```text
STAGING_CHECKOUT_SUCCESS_URL
STAGING_CHECKOUT_CANCEL_URL
STAGING_BILLING_PORTAL_RETURN_URL
STAGING_STRIPE_WEBHOOK_URL
PRODUCTION_CHECKOUT_SUCCESS_URL
PRODUCTION_CHECKOUT_CANCEL_URL
PRODUCTION_BILLING_PORTAL_RETURN_URL
PRODUCTION_STRIPE_WEBHOOK_URL
```

No real URLs are supplied by this slice.

---

## 4. Required mode settings

Safe defaults:

```text
MOCK_STRIPE=true
STRIPE_MODE=test first
self-serve checkout disabled unless owner approves
live mode forbidden until separate live approval
```

Rules:

- mock billing remains the default;
- test mode must run before any live billing;
- first pilot may remain manually managed if the owner chooses;
- self-serve checkout requires explicit owner approval;
- live mode requires a separate live-readiness packet and approval;
- production billing readiness is not granted by config alone.

---

## 5. Required product / price configuration

Owner/operator must provide a reviewed config matrix before checkout/subscription work starts.

| Field | Required? | Status after P3-6b |
|---|---:|---|
| Plan names | Yes | Missing owner answer |
| Test price IDs | Yes before test checkout | Missing owner answer |
| Live price IDs | Yes before live mode | Missing owner answer |
| Monthly pricing | Yes | Missing owner answer |
| Annual pricing, if any | If offered | Missing owner answer |
| Trial length | Yes | Missing owner answer |
| Included contacts/campaigns/agent runs/sends | Yes | Missing owner answer |
| Overage policy | Yes | Missing owner answer |
| Seat/team pricing | If offered | Missing owner answer |
| Entitlement mapping | Yes | Missing owner answer |

Internal entitlements remain controlled by backend plan/config and central gates. Do not trust client-submitted entitlement fields.

---

## 6. Billing readiness state definitions

| State | Definition | Allows money movement? |
|---|---|---:|
| `config_ready` | Required Stripe refs, URLs, mode settings, and price mappings are present and non-placeholder. | No |
| `test_billing_ready` | `config_ready` plus owner-approved test-mode checkout/webhook plan, internal test-card smoke plan, and rollback plan. | No live money |
| `money_ready` | Test-mode smoke passed, evidence attached, refund/chargeback/support owners ready, and owner explicitly approves real money movement. | Limited by approval |
| `production_billing_ready` | Separate production/live approval with production refs, URLs, billing support, incident/rollback owners, tax/legal review if required, and production cutover signoff. | Not granted by P3-6b |

P3-6b grants none of these states by itself. It defines the contract only.

---

## 7. Central gate requirements

Central gates remain non-negotiable:

- `is_active(tenant)`;
- `has_feature(tenant, key)`;
- `can_send`;
- `can_run_agents`;
- `can_create_campaign`;
- `can_export`.

Rules:

- no scattered billing checks;
- no route-level shortcut around central gates;
- no worker bypass;
- no frontend-trusted billing state;
- webhook events may update internal billing state only through an approved service boundary;
- workers must re-check billing gates at claim time;
- state transitions must be audited.

---

## 8. Webhook readiness

Future Stripe webhook implementation must satisfy:

- signature verification before trusting payload fields;
- event ID idempotency;
- duplicate events must not duplicate state changes;
- tenant mapping must be server-side;
- raw webhook payload must not be logged or stored if unsafe;
- processing must be replay-safe;
- event scope remains pending owner answer from P3-6a;
- webhook failures must be observable and auditable;
- webhook endpoint must not trigger money movement by itself.

Initial candidate event scope remains owner-pending:

- checkout completion;
- subscription created/updated/deleted;
- invoice payment success/failure;
- trial ending;
- refund;
- dispute/chargeback;
- other owner-approved events.

---

## 9. Hard stop conditions

Do not begin Stripe implementation or smoke if any of these are true:

- missing Stripe server credential ref;
- placeholder Stripe server credential ref;
- missing webhook signing ref when webhooks are included;
- missing price ID mapping;
- missing checkout success URL;
- missing checkout cancel URL;
- missing portal return URL when portal is enabled;
- webhook signature verification not designed/implemented;
- access matrix unanswered;
- pricing unanswered;
- refund/chargeback rules unanswered;
- billing owner missing;
- billing support owner missing;
- emergency billing-disable owner missing;
- test-mode smoke approval missing;
- live money movement requested without explicit approval;
- central gates bypassed or duplicated outside the gate service;
- any raw credential leakage;
- any real environment file edited with live values;
- production billing approval confused with test-mode readiness.

---

## 10. Remaining owner answers

Still required after P3-6b:

- final provider confirmation;
- test/live mode rules;
- self-serve checkout vs manual first pilot;
- plan/pricing/limits;
- entitlement matrix;
- failed payment/grace/dunning policy;
- refund/chargeback policy;
- webhook event scope;
- Stripe account owner;
- pricing owner;
- billing support owner;
- refund/chargeback approver;
- emergency billing-disable owner;
- test-mode smoke approval;
- live-mode approval.

---

## 11. Final verdict

P3-6b is complete as a Stripe config / secret-readiness contract.

Stripe remains mock/deferred. No SDK, API call, checkout, webhook, real billing, money movement, deployment, production enablement, Resend/live sending, SMS, or live scraping is added or approved.
