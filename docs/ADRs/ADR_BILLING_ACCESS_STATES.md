# ADR — Billing Access States

**Status:** Accepted (state model) — **timing defaults = Owner decision needed**
**Date:** 2026-06-22

## Context

Access decisions cannot rely on Stripe status alone (Stripe status is not enough for access control). Billing must be modeled as data so trials, pricing, feature gates, and usage limits change without a code deploy. Gates run in routes, services, workers, and scheduled jobs.

## Decision

- **Separate `provider_status` (raw Stripe) from `internal_access_state`.** Routes and workers gate **only** on `internal_access_state`.
- Internal access states: `trialing`, `active`, `past_due_grace`, `past_due_locked`, `canceled`, `chargeback_locked`, `unpaid_locked`, `incomplete_locked`.
- **Workers re-check billing at claim time** — a job queued while active must not send if the tenant becomes locked before execution.
- Access behavior per state, blocked-routes list, and always-available list are defined in [BILLING_STATE_MACHINE](../BILLING_STATE_MACHINE.md); schema in [DATABASE_SCHEMA](../DATABASE_SCHEMA.md).

## Options considered

| Option | Verdict |
|---|---|
| Gate directly on Stripe `provider_status` | Rejected — Stripe status alone is insufficient and couples access to provider semantics |
| **Separate internal access state derived from provider events** | **Chosen** — explicit, auditable, provider-independent access control |

## Consequences

- Stripe webhooks update `provider_status`; reconciliation + lifecycle logic derive `internal_access_state`.
- Lock/restore transitions are audited; daily reconciliation flags mismatch.
- Recommended **defaults (not final):** trial **14 days** · grace **7 days** · past-due locked → read-only dashboards/history + billing access · canceled → read-only for retention/export window · chargeback → immediate lock pending manual review.

## Owner decisions / open questions

- [ ] Trial duration (default 14d) — owner decision.
- [ ] Grace period (default 7d) — owner decision.
- [ ] Refund/chargeback policy (default: manual refund review; immediate chargeback lock) — owner decision.
- [ ] Past-due access scope (default: read-only + billing access after lock) — owner decision.

(Defaults are labeled defaults, not committed decisions; confirm in writing before billing launch.)

## Related docs

[BILLING_STATE_MACHINE](../BILLING_STATE_MACHINE.md) · [DATABASE_SCHEMA](../DATABASE_SCHEMA.md) (`tenant_subscriptions`) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)
