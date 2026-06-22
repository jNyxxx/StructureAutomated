# ADR - Billing Access States

**Status:** Accepted - MVP mock billing rules owner-confirmed
**Date:** 2026-06-22

## Context

Access decisions cannot rely on Stripe status alone. Billing must be modeled as data so tenant status, plans, feature gates, and usage limits can be tested deterministically before real money movement. The local MVP must prove centralized billing gates without implementing live Stripe.

## Decision

During the local mock MVP, build only:

- Billing schema.
- Tenant subscription/plan relationship.
- `tenant_status`.
- Centralized access gates.
- Mock billing states and mock transitions.
- Deterministic gate tests.

Do **not** build real Stripe checkout, real Stripe calls, real Stripe webhooks, dunning processing, or money movement during the local MVP. Real Stripe starts later when onboarding the first paying client.

Standardize MVP mock billing states as:

- `trialing`
- `active`
- `past_due`
- `canceled`
- `unpaid`
- `inactive`

Use `inactive` as the catch-all no-access state.

All access must route through one central gate system:

- `is_active(tenant)`
- `has_feature(tenant, key)`

Derived gates must include `can_send`, `can_run_agents`, `can_create_campaign`, and `can_export`.

## Access Rules

During the `past_due` grace period, keep access running.

On `unpaid`, `canceled`, or `inactive`, lock agent runs, cold email/SMS sending, paid ad spend, external paid API calls, and campaign creation.

Keep available longer: dashboard/data read access, exports, and connected integrations as dormant rather than disconnected.

## Later Production Stripe / Dunning Behavior

Production Stripe and dunning rules are later production behavior, not local MVP scope:

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
- Stripe webhooks will later drive `tenant_status`, but not during local MVP.

## Options considered

| Option | Verdict |
|---|---|
| Mock-only MVP billing with centralized gates | Accepted |
| Real Stripe in local MVP | Rejected - premature money movement and webhook complexity before mock demo proof |
| Scattered route/service billing checks | Rejected - access decisions must be centralized and testable |

## Consequences

- MVP billing timing defaults are no longer unresolved because real Stripe is outside local MVP scope.
- Phase 0 must remove real Stripe webhook storage from MVP implementation scope.
- Production billing will need a later implementation phase and evidence bundle before the first paying client.

## Owner decisions / open questions

- [x] MVP mock billing states confirmed.
- [x] MVP mock-only billing scope confirmed.
- [x] Production Stripe/dunning rules documented as later behavior.
- [ ] First-paying-client production billing details, Stripe products/prices, and plan entitlements remain future decisions.

## Related docs

[BILLING_STATE_MACHINE](../BILLING_STATE_MACHINE.md) - [DATABASE_SCHEMA](../DATABASE_SCHEMA.md) - [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)
