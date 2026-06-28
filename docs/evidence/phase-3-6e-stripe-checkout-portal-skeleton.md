# P3-6e — Stripe Checkout / Billing Portal Skeleton

**Purpose:** Add a test-mode-only, fail-closed Stripe checkout and billing portal boundary plus safe API route skeletons without creating real sessions, calling Stripe, or moving money.
**Status:** Complete.
**Date:** 2026-06-29 (Asia/Manila)
**Base commit:** `65450a3 feat(p3-6): add Stripe webhook verification foundation`

---

## 1. Scope and hard stop

P3-6e adds only the fail-closed checkout/portal skeleton.

Confirmed not done:

- no real billing enabled;
- no real Stripe checkout session;
- no real billing portal session;
- no Stripe API call;
- no Stripe SDK/package;
- no real Stripe credentials;
- no real environment file edit;
- no live mode enablement;
- no money movement;
- no tenant billing-state mutation from Stripe;
- no deployment;
- no AWS provisioning;
- no production enablement;
- no Resend/live sending;
- no SMS or live scraping;
- no billing-gate weakening;
- no auth/RBAC/RLS/tenant-isolation bypass.

---

## 2. Provider / service boundary

Added:

```text
backend/app/services/stripe_billing.py
```

Boundary types:

- `StripeBillingProvider`
- `DisabledStripeBillingProvider`
- `StripeBillingAPIService`
- `StripeCheckoutSessionRequest`
- `StripeBillingPortalSessionRequest`
- `StripeSessionResult`

Methods defined for future approved slices:

- `create_checkout_session`
- `create_billing_portal_session`

Current implementation behavior:

- checkout disabled by default returns `STRIPE_CHECKOUT_NOT_AVAILABLE`;
- portal disabled by default returns `STRIPE_PORTAL_NOT_AVAILABLE`;
- enabled but incomplete config returns `STRIPE_CONFIG_NOT_READY`;
- complete test config still returns `STRIPE_BILLING_DISABLED` because this slice does not create sessions;
- no raw secret resolution;
- no Stripe package;
- no provider API call;
- no checkout session creation;
- no billing portal session creation;
- no tenant billing-state mutation;
- no money movement.

---

## 3. Config readiness behavior

Safe defaults remain:

```text
MOCK_STRIPE=true
STRIPE_MODE=test
STRIPE_CHECKOUT_ENABLED=false
STRIPE_BILLING_PORTAL_ENABLED=false
```

Added placeholder-only config fields:

```text
STRIPE_SECRET_KEY_REF
STRIPE_SUCCESS_URL
STRIPE_CANCEL_URL
STRIPE_PORTAL_RETURN_URL
STRIPE_PRICE_IDS_REF
```

Existing webhook config remains:

```text
STRIPE_WEBHOOKS_ENABLED=false
STRIPE_WEBHOOK_SECRET_REF=<placeholder>
```

Readiness helper added:

```text
stripe_billing_config_failures(settings)
```

It checks only safe refs and URLs. It never resolves raw secret values and never validates with Stripe.

---

## 4. Route behavior

Added route skeletons:

```text
POST /api/v1/billing/checkout-session
POST /api/v1/billing/portal-session
```

Route behavior:

- requires authenticated tenant principal;
- uses `tenant_session(tenant_id=principal.tenant_id, actor_id=principal.user_id)` before DB-backed billing gate setup;
- calls service layer only;
- does not trust `tenant_id` from client body;
- rejects unexpected body fields;
- uses central RBAC/billing service boundary;
- returns safe error envelopes only while disabled/incomplete;
- does not return raw secrets, price ids, or internal config;
- does not call Stripe;
- does not create checkout or portal sessions;
- does not move money;
- does not mutate tenant billing state.

---

## 5. Billing gate safety

Preserved central gates:

- `is_active(tenant)`;
- `has_feature(tenant, key)`;
- `can_send`;
- `can_run_agents`;
- `can_create_campaign`;
- `can_export`.

This slice does not unlock any paid/write/outbound feature. Workers still must re-check billing gates at claim time.

---

## 6. Boot guard behavior

Boot guard now blocks unsafe checkout/portal enablement in staging and production.

Checkout-enabled config requires:

- non-placeholder Stripe server credential ref;
- safe success URL;
- safe cancel URL;
- price ids ref;
- test mode only unless separate live approval exists.

Portal-enabled config requires:

- non-placeholder Stripe server credential ref;
- safe portal return URL;
- test mode only unless separate live approval exists.

`controlled_demo` does not bypass Stripe checkout/portal requirements.

Existing webhook, Resend, Redis, auth, RLS, and billing guard checks were not weakened.

---

## 7. Tests added / updated

Added:

```text
backend/tests/test_stripe_billing.py
```

Updated:

```text
backend/tests/test_router_billing.py
backend/tests/test_boot_guard.py
```

Coverage added:

- mock billing remains default;
- checkout disabled by default;
- portal disabled by default;
- checkout provider fails closed when disabled;
- portal provider fails closed when disabled;
- incomplete config fails closed;
- complete test config still does not create checkout session;
- complete test config still does not create billing portal session;
- Stripe billing service requires billing permission;
- live mode fails readiness without separate approval;
- routes require auth;
- routes are mounted;
- checkout endpoint fails closed while disabled;
- portal endpoint fails closed while disabled;
- routes reject client-supplied tenant id;
- route errors are safe;
- source has no Stripe SDK/API/network/session-creation markers;
- production/staging boot guard blocks unsafe enabled checkout/portal config;
- controlled demo does not bypass checkout/portal requirements;
- existing mock billing API tests still pass.

---

## 8. Local verification results

Focused backend checks passed before full gates:

```text
python -m ruff check app tests/test_stripe_billing.py tests/test_router_billing.py tests/test_boot_guard.py
python -m black --check app tests/test_stripe_billing.py tests/test_router_billing.py tests/test_boot_guard.py
python -m mypy app --ignore-missing-imports
python -m pytest -q tests/test_stripe_billing.py tests/test_router_billing.py tests/test_boot_guard.py
```

Full backend result:

```text
ruff PASS
black PASS — 214 files would be left unchanged
mypy PASS — no issues found in 156 source files
pytest PASS — 726 passed, 1 warning in 45.12s
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
backend Docker build PASS — automatedstructure-backend:p3-6e-local, image 9ec61a2308cb, 261MB
frontend Docker build PASS — automatedstructure-frontend:p3-6e-local, image c39f0cb6c1d3, 158MB
```

Known warnings:

- existing FastAPI/Starlette TestClient deprecation warning;
- existing npm audit report: 10 findings;
- existing Vite CJS deprecation warning;
- expected frontend backend-unavailable fallback stderr in tests.

---

## 9. Honest limits

Still not implemented:

- real checkout session creation;
- real billing portal session creation;
- Stripe SDK/package;
- Stripe API calls;
- raw secret resolution;
- real credentials;
- test-card smoke;
- tenant billing-state mutation from Stripe;
- subscription/entitlement sync from Stripe;
- money movement;
- live billing;
- deployment;
- production enablement.

---

## 10. Final verdict

P3-6e is complete as a fail-closed Stripe checkout and billing portal skeleton.

Real billing remains disabled. Checkout and billing portal session creation remain unavailable until a later approved test-mode slice.
