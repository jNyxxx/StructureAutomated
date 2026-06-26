# Phase 3-1a — Boot-guard RLS coverage + controlled_demo attestation

**Date:** 2026-06-26
**Scope:** P3-1a production safety hardening (first P3-1 implementation slice).
**Runtime:** Local/mock only.
**Production status:** Not approved (unchanged). No providers / sending / Stripe / SMS / OAuth /
live-scraping enabled. No migrations run. No live adapter registered.

## Summary

Closes the two first-priority gaps surfaced by the P3-1 audit
([phase-3-1-production-readiness-audit.md](phase-3-1-production-readiness-audit.md)):

1. **Boot-guard RLS coverage** expanded from **2 → 29** tenant-owned tables.
2. **controlled_demo owner-approval attestation** added — fails closed in production when the
   escape hatch is set without a recorded approver.

Both are detection/governance reinforcements. No safety gate was weakened; no live path created.

## Authoritative table count (correction: 23 → 29)

The migrations force RLS (ENABLE + FORCE) on **30** tables, applied two ways:

- `app/db/rls.py::apply_forced_rls(table)` helper — **21** tables (each also gets the standard
  `<table>_tenant_isolation` policy keyed on `app.current_tenant_id`).
- Literal `ALTER TABLE … ENABLE/FORCE ROW LEVEL SECURITY` — **9** tables.

Cross-checked against SQLAlchemy `Base.metadata`: **all 25 model tables carrying `tenant_id` are
covered** — there is no real RLS hole. `plans` and `users` are global (no `tenant_id`); `tenants`
is keyed on its own `id`.

The boot guard now verifies **29** = the 30 forced-RLS tables **minus `audit_events`**, which
remains the one documented exception (immutable, stores tenant + platform events, non-standard
policy; preserved rather than silently reversed). The prior audit's "23" was an under-estimate;
the evidence-based figure is **29**.

The 29 verified tables: auth_sessions, campaign_contacts, campaign_roi_assumptions, campaigns,
compliance_profiles, contact_import_rows, contact_imports, contacts, draft_evidence, drafts,
followup_rules, followup_schedules, idempotency_keys, integration_credentials, jobs,
knowledge_chunks, knowledge_documents, outbound_messages, outcome_events, research_artifacts,
research_runs, review_items, safety_gate_results, send_gate_results, support_access_grants,
suppressions, tenant_memberships, tenant_subscriptions, tenants.

## Changes

| File | Change |
|------|--------|
| `backend/app/config.py` | New `controlled_demo_approved_by: str \| None = None` attestation field. |
| `backend/app/observability/boot_guard.py` | `TENANT_OWNED_TABLES` expanded 2 → 29 (audit_events still excluded); `config_failures()` adds a fail-closed attestation check around `controlled_demo` (reusing `_is_placeholder`). `database_failures()` loop unchanged — automatically covers all 29. |
| `backend/tests/test_boot_guard.py` | 2 existing tests updated; 10 new tests added (see below). |

`main.py` and `workers/bootstrap.py` already call `enforce_config` + `database_failures`, so both
the API and the worker pick up the wider coverage and the attestation gate with no wiring change.

### controlled_demo behavior (production)

| Condition | Result |
|---|---|
| mock providers + `controlled_demo=False` | fail (mock providers in production) — unchanged |
| `controlled_demo=True`, approver blank/placeholder | **fail closed** (new) |
| `controlled_demo=True`, real approver | mock-provider exception permitted; still no live path (registry empty) |

## Tests

Updated: `test_mocks_in_production_fail_unless_controlled_demo` (now supplies an approver);
`test_audit_events_exempt_from_forced_rls_check` (asserts the full 29-set, audit_events still out).

Added: `test_tenant_owned_set_is_exact` · `test_boot_guard_covers_every_model_tenant_table`
(drift-proof: every tenant_id model table must be covered) · `test_all_tables_rls_ok_passes_database_check`
· `test_rls_not_enabled_fails_database_check` · `test_rls_not_forced_fails_database_check`
· `test_controlled_demo_without_attestation_fails_closed` · `test_controlled_demo_with_attestation_passes`
· `test_controlled_demo_placeholder_attestation_fails` · `test_controlled_demo_requires_attestation_even_without_mocks`
· `test_adapter_registry_has_no_live_provider_paths`.

The `database_failures()` RLS tests use a fake `AsyncConnection` (dispatch by SQL substring) so they
are deterministic without Postgres; the live `alembic upgrade` + DB-state check still runs in CI.

## Gate results

| Gate | Result |
|---|---:|
| Backend `ruff check app tests` | PASS |
| Backend `black --check app tests` | PASS |
| Backend `mypy app` | PASS (145 source files) |
| Backend `pytest` | PASS — **525 passed** (515 + 10 new) |
| Frontend `npm run lint` | PASS |
| Frontend `npm run typecheck` | PASS |
| Frontend `npm run test` | PASS — **122 passed** |
| Frontend `npm run build` | PASS |

## Safety confirmation

No production enabled · no real providers / sending / Stripe / SMS / OAuth / live scraping · no real
`.env` secrets touched · no migrations authored or run · no live adapter registered (registry still
empty; `resolve()` raises `KeyError`) · auth / RLS / tenant isolation / billing gates / send gates
unchanged and not weakened. Frontend untouched (gates run only to prove no regression).
