# P3-6a — Stripe / Real Billing Owner Decision Packet

**Purpose:** Capture owner decisions required before any Stripe implementation, checkout, webhook, dunning, billing portal, or money movement.
**Status:** Owner decision packet created; unanswered.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `22f56c0 docs(p3-5): define Resend smoke readiness contract`

---

## 1. Scope and hard stop

P3-6a is documentation only.

Confirmed not done:

- no Stripe implementation;
- no Stripe package or SDK;
- no Stripe credentials;
- no Stripe API call;
- no checkout session;
- no billing portal;
- no Stripe webhook;
- no invoice/payment/dispute handling;
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

Hard warning: do not add Stripe packages, API calls, checkout, webhooks, real charges, or live money movement until this packet is answered and the specific implementation slice is separately approved.

---

## 2. Current mock billing state

Current implementation is local/mock only:

- plan and tenant subscription schema exists;
- standardized tenant states exist: `trialing`, `active`, `past_due`, `canceled`, `unpaid`, `inactive`;
- central access gates exist through `is_active(tenant)` and `has_feature(tenant, key)`;
- derived gates exist for `can_send`, `can_run_agents`, `can_create_campaign`, and `can_export`;
- `past_due` can remain active only inside a grace window;
- `unpaid`, `canceled`, and `inactive` lock paid/write/send actions;
- mock/local billing APIs exist for subscription/access/usage/state transition;
- audit exists for mock state transitions;
- tests prove no real Stripe or money path is present.

Current defaults remain:

```text
MOCK_STRIPE=true
real billing disabled
money movement disabled
```

---

## 3. Owner decision form

### 3.1 Billing provider

Owner must select one:

- [ ] Stripe selected for first real billing provider.
- [ ] Stripe delayed; keep mock/manual billing only.
- [ ] No provider yet; revisit after first paying-client terms are signed.
- [ ] Other provider: `____________________________`

Required notes:

```text
Selected provider:
Reason:
Decision owner:
Decision date:
```

### 3.2 Billing mode

Owner must decide:

- [ ] Test mode first is required.
- [ ] Live mode later requires separate approval.
- [ ] Self-serve checkout allowed.
- [ ] Self-serve checkout not allowed for first pilot.
- [ ] First pilot billing is manually managed.
- [ ] Billing portal allowed.
- [ ] Billing portal deferred.

Required fill-ins:

```text
First billing mode:
Allowed checkout audience:
Billing portal allowed? yes/no
Manual billing fallback? yes/no
Approval required before live mode:
```

### 3.3 Plans / pricing

Owner must define all first-client plan terms.

| Field | Owner answer |
|---|---|
| Plan name(s) |  |
| Monthly price |  |
| Annual price, if any |  |
| Trial length |  |
| Included contacts |  |
| Included campaigns |  |
| Included AI agent runs |  |
| Included sends |  |
| Overage policy |  |
| Seat/team pricing |  |
| Upgrade/downgrade rules |  |
| Tax/VAT handling owner |  |
| Invoice language/branding owner |  |

### 3.4 Access rules by billing state

Owner must confirm what each state can/cannot do.

| State | Create campaigns | Run agents | Generate drafts | Approve/send | Export | Analytics | Team/settings | Owner notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `trialing` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `active` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `past_due` in grace | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `past_due` after grace | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `unpaid` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `canceled` before period end | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `canceled` after period end | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `inactive` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |  |

Non-negotiable engineering rule: route all access through central billing gates only. Do not scatter billing checks across routes, services, or workers.

### 3.5 Payment failure rules

Owner must decide:

| Field | Owner answer |
|---|---|
| Grace period days |  |
| Reminder schedule |  |
| Retry/dunning schedule |  |
| When create campaign locks |  |
| When agent runs lock |  |
| When draft generation locks |  |
| When send/approve locks |  |
| When export locks |  |
| Who can override |  |
| Override max duration |  |
| Required audit details |  |
| Customer-facing copy owner |  |

### 3.6 Refund / chargeback rules

Owner must decide:

| Field | Owner answer |
|---|---|
| Refund policy |  |
| Partial refund policy |  |
| Chargeback/dispute handling |  |
| Access lock immediately on chargeback? |  |
| Who approves refund |  |
| Who approves dispute response |  |
| Required audit evidence |  |
| Customer-support owner |  |

### 3.7 Stripe objects

Owner/operator must confirm which objects are in scope for first implementation:

- [ ] Products.
- [ ] Prices.
- [ ] Customers.
- [ ] Subscriptions.
- [ ] Checkout sessions.
- [ ] Billing portal.
- [ ] Invoices.
- [ ] Payment methods.
- [ ] Promotion codes/coupons.
- [ ] Tax settings.

Required mapping:

| Internal concept | Stripe object / value | Owner/operator answer |
|---|---|---|
| Tenant | Customer metadata / customer record |  |
| Plan | Product + price |  |
| Subscription | Subscription |  |
| Trial | Subscription trial |  |
| Billing state | Subscription / invoice lifecycle mapping |  |
| Entitlements | Internal plan features, not trusted from client |  |

### 3.8 Webhook scope

Owner/operator must approve the initial webhook scope.

Candidate events:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.trial_will_end`
- `charge.refunded`
- `charge.dispute.created`
- other needed events: `____________________________`

Non-negotiable requirements:

- webhook signature verification required;
- idempotency required by provider event ID;
- raw webhook payloads must not be logged or exposed;
- processing must be safe to replay;
- duplicate events must not create duplicate billing transitions;
- no tenant ID from webhook body may be trusted without server-side mapping.

### 3.9 Secrets / config

Owner/operator must provide or approve config references only.

| Config item | Required? | Owner/operator answer |
|---|---:|---|
| Stripe server credential ref | Yes before test-mode API call |  |
| Stripe webhook signing credential ref | Yes before webhook verification |  |
| Price IDs | Yes before checkout/subscription |  |
| Success URL | Yes before checkout |  |
| Cancel URL | Yes before checkout |  |
| Billing portal return URL | If portal enabled |  |
| Test-mode indicator | Yes |  |
| Live-mode approval ref | Only for later live mode |  |

Rules:

- no raw Stripe credentials in DB;
- no raw Stripe credentials in logs;
- no raw Stripe credentials in frontend config;
- no raw Stripe credentials in audit events;
- no raw Stripe credentials in prompts or docs;
- price IDs may be stored as reviewed config mappings.

### 3.10 Safety / launch requirements

Owner must confirm:

- [ ] Test mode first.
- [ ] Internal/test-card smoke first.
- [ ] No real money until explicit live-mode approval.
- [ ] Fail closed if Stripe config is incomplete.
- [ ] Central billing gates remain authoritative: `is_active(tenant)`, `has_feature(tenant, key)`.
- [ ] No scattered billing checks.
- [ ] No route bypass.
- [ ] All billing events audited.
- [ ] Webhook signature verification required.
- [ ] Duplicate webhook/event processing is idempotent.
- [ ] Refund/chargeback actions require owner-approved policy.

### 3.11 Owners

Owner must fill in:

| Role | Name / owner |
|---|---|
| Stripe account owner |  |
| Pricing owner |  |
| Plan/entitlement owner |  |
| Refund approver |  |
| Chargeback/dispute approver |  |
| Billing support owner |  |
| Emergency billing-disable owner |  |
| Technical implementation approver |  |
| Live-mode cutover approver |  |

---

## 4. What is already implemented

Already implemented in local/mock mode:

- plan and tenant subscription schema;
- tenant subscription state;
- mock state transitions;
- centralized billing gate service;
- derived feature gates;
- protected billing API read endpoints;
- mock billing state transition endpoint;
- mock usage aggregation;
- audit on mock state changes;
- tests for states, gates, and access snapshots.

---

## 5. What remains missing before real billing

Missing before any Stripe/test billing implementation:

- answered owner packet;
- provider decision confirmed;
- plan/pricing table;
- entitlement matrix;
- payment failure/grace/dunning policy;
- refund/chargeback policy;
- Stripe account owner;
- config reference contract;
- webhook scope approval;
- test-mode checkout/portal decision;
- test-mode smoke approval;
- failure/rollback plan;
- live-mode approval process.

Missing before live money movement:

- green test-mode smoke evidence;
- owner live-mode approval;
- production credential refs;
- production domain/URL values;
- support/refund/dispute process;
- legal/tax/invoice review if required;
- rollback/emergency billing-disable owner;
- production deployment approval.

---

## 6. Proposed implementation slices

| Slice | Purpose | Constraints |
|---|---|---|
| P3-6b | Stripe config/secret contract | Docs/config validation only; no SDK/API call unless separately approved. |
| P3-6c | Stripe webhook verification foundation | Signature verification + idempotency + normalization only; no money movement. |
| P3-6d | Stripe checkout/billing portal skeleton | Test-mode only; no live mode; behind owner-approved config. |
| P3-6e | Internal test-mode billing smoke | Test card only; no live money; evidence required. |
| P3-6f | Live billing readiness packet | Docs/approval packet for live mode; no live cutover by itself. |

Each slice requires explicit approval before starting.

---

## 7. Hard stop conditions

Do not start Stripe implementation if any of these are true:

- owner packet unanswered;
- provider not selected;
- plan/pricing incomplete;
- access-state behavior unresolved;
- grace/dunning rules unresolved;
- refund/chargeback rules unresolved;
- owners missing;
- config refs missing;
- webhook scope unresolved;
- live-mode approval requested before test-mode evidence;
- any proposal bypasses central billing gates;
- any proposal stores raw Stripe credentials outside approved secret management;
- any proposal allows live money movement without explicit approval.

---

## 8. Final verdict

P3-6a creates the Stripe / real billing owner decision packet.

Stripe remains deferred. No package, API call, checkout, webhook, charge, live billing, or money movement is reachable from this slice.
