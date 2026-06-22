# Billing State Machine

**Purpose:** Subscription/access state model, route + worker locks, Stripe (mock/live) workflow, webhook safety, reconciliation, and billing audit. **Provider status and internal access state are separate concerns.** Parameter defaults (trial/grace/etc.) are owner decisions.
**Source sections:** Master guide §12 (billing and subscription).
**Status:** Draft (parameter defaults = **Owner decision needed** → [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md))
**Related docs:** [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (`tenant_subscriptions`, `stripe_webhook_events`) · [API_CONTRACT](API_CONTRACT.md) (billing/webhook routes) · [CLAUDE](../CLAUDE.md) (rule 8 gates everywhere) · [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md)

---

## 1. Implementation defaults (owner-overridable)

Billing is modeled as **data**, so trials/pricing/feature gates/usage limits change without a code deploy.

| Default | Value | Authority |
|---|---|---|
| Trial | 14 days | Owner decision → ADR |
| Grace after failed payment | 7 days | Owner decision → ADR |
| Past-due during locked state | read-only dashboards/history + billing access | Owner decision → ADR |
| Canceled tenants | read-only for retention/export window | Owner decision → ADR |
| Chargeback | immediate lock pending manual review | Owner decision → ADR |

## 2. Provider status vs internal access state

- **Provider status** (`provider_status`): raw Stripe state — never the access authority.
- **Internal access state** (`internal_access_state`): the only thing routes/workers gate on. Stored separately (see [DATABASE_SCHEMA §6](DATABASE_SCHEMA.md)).

## 3. Access states

| State | Product access | Write actions | Billing/settings | Worker actions |
|---|---|---|---|---|
| `trialing` | Full within trial quota | Allowed | Allowed | Allowed within quota |
| `active` | Full within plan quota | Allowed | Allowed | Allowed within quota |
| `past_due_grace` | Full during 7-day grace | Allowed w/ warnings | Allowed | Allowed w/ warnings |
| `past_due_locked` | Read-only dashboards/history | Blocked | Allowed | Block new jobs; finish safe non-send jobs only |
| `canceled` | Read-only retention/export | Blocked | Invoices/export only | Blocked except export/delete jobs |
| `chargeback_locked` | Read-only + support/billing | Blocked | Allowed | Blocked except admin-approved remediation |
| `unpaid_locked` / `incomplete_locked` | Billing/support only | Blocked | Allowed | Block paid jobs |

**Routes blocked outside `active`/`trialing`/`grace`:** campaign create/start/resume · CSV import (except approved correction import) · agent run + draft generation · approval-to-send/schedule · mailbox creation · provider credential add/update · non-required exports.

**Always available:** login · billing status · checkout/portal · settings needed to resolve billing · legal data export/delete request · support contact.

## 4. Worker locks

Workers **re-check billing at claim time** (CLAUDE rule 8). A job created while `active` must **not** send if the tenant becomes locked before execution.

## 5. Stripe workflow

- Checkout creation uses Stripe live/mock adapter.
- **Verify Stripe raw-body signature before parsing.**
- Store every event in `stripe_webhook_events` with unique event ID; return 2xx **only after durable storage**.
- Process billing state **asynchronously via queue**, idempotently. Failed processing leaves event retryable.
- **Daily reconciliation** compares local state to Stripe.

Handle at minimum: `checkout.session.completed` · `customer.subscription.created` · `customer.subscription.updated` · `customer.subscription.deleted` · `invoice.payment_succeeded` · `invoice.payment_failed` · `charge.refunded` · `charge.dispute.created` · `charge.dispute.closed`.

## 6. Billing audit

Audit: checkout, subscription changes, payment success/failure, cancellation, chargeback, access lock/restore, and reconciliation mismatch.

## 7. Acceptance criteria

- [ ] Provider status stored separately from internal access state.
- [ ] Locks enforced in routes **and** workers (claim-time re-check).
- [ ] Stripe signature verified; events stored before 2xx; processing idempotent.
- [ ] Daily reconciliation detects and flags mismatch.
- [ ] Failed-payment lock + chargeback lock behave per state table.
