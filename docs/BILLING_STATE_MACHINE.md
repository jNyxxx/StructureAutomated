# Billing State Machine

**Purpose:** MVP mock billing access states, tenant status, centralized gates, and later production Stripe/dunning behavior. Local MVP billing is mock-only; real Stripe is deferred until first-paying-client onboarding.
**Source sections:** Master guide §12 (billing and subscription).
**Status:** Draft (MVP mock billing rules = owner-confirmed -> [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md))
**Related docs:** [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md) - [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (`tenant_subscriptions`) - [API_CONTRACT](API_CONTRACT.md) (billing status routes) - [CLAUDE](../CLAUDE.md) (rule 8 gates everywhere) - [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md)

---

## 1. MVP billing scope

During the local mock MVP, build only:

- Billing schema.
- Tenant subscription/plan relationship.
- `tenant_status`.
- Centralized access gates.
- Mock billing states and mock transitions.
- Deterministic gate tests.

Do **not** build real Stripe checkout, real Stripe calls, real Stripe webhooks, dunning processing, or money movement during the local MVP. Real Stripe starts later when the first paying client is being onboarded.

P3-6a update (2026-06-28): the Stripe / real billing owner decision packet now exists at [evidence/phase-3-6a-stripe-billing-owner-decision-packet.md](evidence/phase-3-6a-stripe-billing-owner-decision-packet.md). It is unanswered and grants no implementation approval. Stripe remains deferred; no SDK, API call, checkout, webhook, real billing, or money movement is approved.

P3-6b update (2026-06-28): the Stripe config / secret-readiness contract now exists at [evidence/phase-3-6b-stripe-config-secret-readiness-contract.md](evidence/phase-3-6b-stripe-config-secret-readiness-contract.md). It defines required refs, URLs, mode settings, product/price mappings, readiness states, central gate requirements, webhook readiness, hard stops, and remaining owner answers. It grants no config/test/money/production readiness state.

P3-6c update (2026-06-28): safe owner defaults are recorded at [evidence/phase-3-6c-stripe-owner-defaults.md](evidence/phase-3-6c-stripe-owner-defaults.md). Defaults select Stripe as the future provider direction, keep mock billing as default, require test mode first, disable self-serve checkout by default, define placeholder internal plans, set a 14-day trial default, map billing-state access defaults, and keep central gates authoritative. Real billing remains disabled.

P3-6d update (2026-06-29): the Stripe webhook verification foundation now exists at [evidence/phase-3-6d-stripe-webhook-verification-foundation.md](evidence/phase-3-6d-stripe-webhook-verification-foundation.md). It adds signature verification, safe event normalization, idempotency boundary, fail-closed route behavior, and boot-guard checks only. It does not add checkout, billing portal, Stripe API calls, tenant billing-state mutation, real billing, or money movement.

P3-6e update (2026-06-29): the Stripe checkout / billing portal skeleton now exists at [evidence/phase-3-6e-stripe-checkout-portal-skeleton.md](evidence/phase-3-6e-stripe-checkout-portal-skeleton.md). It adds a disabled provider boundary, fail-closed checkout/portal endpoints, safe config placeholders, and boot-guard checks only. It does not create checkout sessions, create billing portal sessions, call Stripe, mutate billing state, enable real billing, or move money.

## 2. MVP mock billing states

| State | Meaning | Default access |
|---|---|---|
| `trialing` | Trial access | Full access within plan limits |
| `active` | Active subscription/access | Full access within plan limits |
| `past_due` | Payment issue inside grace period | Keep access running during grace |
| `canceled` | Canceled or period-ended customer | Locked for paid/write/send actions |
| `unpaid` | Dunning exhausted / unpaid | Locked for paid/write/send actions |
| `inactive` | Catch-all no-access state | Locked for paid/write/send actions |

Use `inactive` as the catch-all no-access state.

## 3. Central gates

Access must route through one central gate system:

- `is_active(tenant)`
- `has_feature(tenant, key)`

Do not scatter billing `if` checks across routes, services, workers, or scheduled jobs.

Derived gates must include:

- `can_send`
- `can_run_agents`
- `can_create_campaign`
- `can_export`

Routes and workers must re-use these gates. Workers re-check billing at claim time.

## 4. Lock behavior

During `past_due` grace, keep access running.

On `unpaid`, `canceled`, or `inactive`, lock:

- Agent runs.
- Cold email/SMS sending.
- Paid ad spend.
- External paid API calls.
- Campaign creation.

Keep available longer:

- Dashboard/data read access.
- Exports.
- Connected integrations as dormant, not disconnected.

## 5. Later production Stripe / dunning behavior

The following rules are documented for the later first-paying-client / production billing phase, not the local MVP. They are planning placeholders only until the P3-6a owner packet is answered:

- `trialing` = full access during trial.
- Trial ends with no payment method -> `inactive`.
- `active` = full access.
- Failed payment -> `past_due` and start dunning.
- Retry schedule: immediate, 24h, day 3, day 7.
- Grace period = 7 days during `past_due`.
- After retries plus grace exhausted -> `unpaid`, then canceled/inactive locked.
- Customer cancellation = `canceled`; access continues until paid period ends, then locks.
- Full refund = canceled/inactive.
- Chargeback/dispute = immediate `inactive` hard stop and manual review.
- Stripe webhooks will later drive `tenant_status`, but P3-6d does not mutate tenant billing state yet.

## 6. Billing audit

Audit mock state changes, access locks/restores, gate denials for paid actions, and later production Stripe lifecycle events.

## 7. Acceptance criteria

- [ ] MVP billing schema stores plan/subscription relationship and tenant status.
- [ ] Only the standardized MVP states are accepted: `trialing`, `active`, `past_due`, `canceled`, `unpaid`, `inactive`.
- [ ] `is_active(tenant)` and `has_feature(tenant, key)` are the only access authorities.
- [ ] Derived gates cover send, agent runs, campaign creation, and export.
- [ ] Locked states block routes and workers at claim time.
- [ ] Deterministic tests cover every mock transition and gate.
- [ ] No real Stripe checkout, calls, webhooks, dunning, or money movement exists in local MVP.
