# P3-6c — Stripe Billing Owner Defaults

**Purpose:** Record safe default answers to the Stripe billing decision packet so later billing work can proceed without guessing.
**Status:** Docs-only owner-defaults record complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `76a3f17 docs(p3-6): define Stripe config readiness contract`

---

## 1. Scope and hard stop

P3-6c is documentation only.

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

## 2. Billing provider default

Default owner answer:

- Stripe is the selected provider direction for future real billing.
- Mock billing remains default until a Stripe test-mode slice is implemented and separately approved.
- Manual billing remains allowed for the first pilot if checkout is not yet proven.

This does not approve Stripe implementation or any provider call.

---

## 3. Billing mode defaults

Default owner answers:

| Item | Safe default |
|---|---|
| First mode | Test mode first |
| Live mode | Later only after separate live-money approval |
| First pilot | May be manually managed until checkout is proven |
| Self-serve checkout | Disabled by default until approved |
| Billing portal | Deferred until owner approves |
| Public pricing page changes | None in this slice |

---

## 4. Plans / pricing defaults

Placeholder internal plan structure only:

| Internal plan | Purpose | Public price status |
|---|---|---|
| Starter / Pilot | First controlled pilot tier | Owner confirmation required |
| Growth | Standard paid growth tier | Owner confirmation required |
| Scale | Higher-volume tier | Owner confirmation required |

Defaults:

- Final public prices remain owner-confirmation-required.
- No public pricing page changes are approved in this slice.
- Trial default is 14 days unless owner changes it.
- Usage limits remain controlled by existing feature gates and tenant subscription config.
- Included contacts/campaigns/agent runs/sends remain owner-confirmation-required.
- Overage policy remains owner-confirmation-required.
- Seat/team pricing remains owner-confirmation-required.

---

## 5. Access matrix defaults

| Billing state | Create campaigns | Run agents | Generate drafts | Approve/send | Export | Analytics | Team/settings |
|---|---|---|---|---|---|---|---|
| `trialing` | Allow within limits | Allow within limits | Allow within limits | Allow within limits | Allow within limits | Allow | Allow |
| `active` | Allow within limits | Allow within limits | Allow within limits | Allow within limits | Allow within limits | Allow | Allow |
| `past_due` in grace | Allow, billing risk flagged | Allow, billing risk flagged | Allow, billing risk flagged | Allow, billing risk flagged | Allow, billing risk flagged | Allow | Allow billing/settings management |
| `past_due` after grace | Block costly/outbound actions | Block | Block | Block | Owner policy pending; default block if costly | Allow read-only | Allow billing/account recovery |
| `unpaid` | Block costly/outbound actions | Block | Block | Block | Owner policy pending; default block if costly | Allow read-only/recovery only | Allow billing/account recovery |
| `canceled` before period end | Allow until period end unless owner overrides | Allow until period end unless owner overrides | Allow until period end unless owner overrides | Allow until period end unless owner overrides | Allow until period end unless owner overrides | Allow | Allow billing/settings management |
| `canceled` after period end | Block costly/outbound actions | Block | Block | Block | Owner policy pending; default block if costly | Allow read-only/recovery only | Allow billing/account recovery |
| `inactive` | Block | Block | Block | Block | Block | No access except account/billing recovery basics | Account/billing recovery basics only |

Central gate note:

- These defaults must be enforced through `is_active(tenant)` and `has_feature(tenant, key)` only.
- Derived gates remain `can_send`, `can_run_agents`, `can_create_campaign`, and `can_export`.
- Do not scatter billing checks across routes, workers, services, or frontend code.

---

## 6. Payment failure defaults

Default grace period:

```text
7 days
```

Default reminder/lock schedule:

| Day | Action |
|---:|---|
| Day 0 | Payment failed; mark billing risk; send first reminder if messaging is approved. |
| Day 3 | Reminder. |
| Day 6 | Final reminder. |
| Day 7 | Lock costly/outbound features if still unresolved. |

Owner override rules:

- Owner override is allowed only through an audited administrative action.
- Override must record owner, reason, timestamp, previous state, new state, and expiry if temporary.
- Override must not bypass central billing gates; it should update the state/entitlement source consumed by the gates.

---

## 7. Refund / chargeback defaults

Refund defaults:

- Refunds require owner approval.
- Refund actions must be audited.
- Refund policy remains owner-confirmation-required before live mode.

Chargeback defaults:

- Chargebacks immediately flag the account for review.
- Chargebacks may lock costly/outbound actions until reviewed.
- Chargeback/dispute actions must be audited.
- Dispute response owner remains owner/operator until delegated.

---

## 8. Stripe object scope defaults

Default future object scope:

- customer;
- product;
- price;
- subscription;
- checkout session later;
- billing portal later;
- invoice;
- payment method reference only.

Rules:

- No raw card/payment data is stored by AutomatedStructure.
- Payment method handling must stay inside Stripe-hosted flows or approved token/reference boundaries.
- Internal entitlements remain server-side and are not trusted from client input.

---

## 9. Webhook scope defaults

Default future event scope:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.trial_will_end`
- `charge.refunded`
- `charge.dispute.created`

Webhook requirements:

- signature verification required before trusting payload fields;
- provider event idempotency required;
- duplicate events must not duplicate state changes;
- raw webhook payload leakage is not allowed;
- tenant mapping must be server-side;
- webhook processing must be replay-safe;
- webhook endpoint must not create money movement by itself.

---

## 10. Secrets / config defaults

Defaults are references/placeholders only:

- `STRIPE_SECRET_KEY_REF` placeholder only;
- `STRIPE_WEBHOOK_SECRET_REF` placeholder only;
- `STRIPE_PRICE_ID_*` refs placeholder only;
- success/cancel/portal URLs separate for staging and production;
- no raw Stripe keys in DB, logs, frontend, audit events, prompts, evidence, or Git.

No real values are supplied in P3-6c.

---

## 11. Safety / launch defaults

Defaults:

- Mock billing remains default.
- No live money movement until separate approval.
- Test-card smoke only in a later approved slice.
- Central billing gates remain authoritative:
  - `is_active(tenant)`;
  - `has_feature(tenant, key)`;
  - `can_send`;
  - `can_run_agents`;
  - `can_create_campaign`;
  - `can_export`.
- No scattered billing checks.
- No route/service/worker bypass.
- Billing state changes must be audited.

---

## 12. Owner defaults

Safe owner defaults until named people are provided:

| Role | Default owner |
|---|---|
| Stripe account owner | owner/operator unless named later |
| Pricing owner | owner/operator |
| Refund approver | owner/operator |
| Chargeback/dispute approver | owner/operator |
| Billing support owner | owner/operator until delegated |
| Emergency billing-disable owner | owner/operator + engineering |

Named owners are still required before any live-money readiness claim.

---

## 13. Remaining exact values

Still required:

- final plan names;
- final public prices;
- final usage limits;
- final Stripe account owner name;
- final billing support owner name;
- final refund/chargeback approver name;
- test-mode secret refs;
- test price IDs;
- test-mode smoke approval window;
- live-mode approval for any future money movement.

---

## 14. Final verdict

P3-6c records safe owner defaults for the Stripe billing lane.

Real billing remains disabled. Mock billing remains default. No Stripe implementation, SDK/package, API call, checkout, webhook, credentials, deployment, production enablement, Resend/live sending, SMS, live scraping, or money movement was added.
