# P4-RLSDefenseInDepth-Fix

**Date:** 2026-07-03
**Branch:** master
**Base commit:** 1f61375
**Status:** Complete

## Scope

Two live backend read/update paths relied only on Postgres RLS with no explicit app-level tenant filter:

1. `backend/app/repositories/tenant_repo.py` — `get_current_tenant()`, `update_current_tenant()`, wired to `GET /api/v1/tenants/current` and `PATCH /api/v1/tenants/current`.
2. `backend/app/audit/repository.py` — `list_recent_bounded()`, wired to `GET /api/v1/audit-events`.

This slice adds explicit tenant scoping to both paths as defense-in-depth on top of RLS, per CLAUDE.md rule 6 ("RLS is required but not enough. Every route needs permission checks and object-ownership checks."). Frontend readiness auditing is explicitly out of scope for this slice.

## Bug/gap summary

**Affected files:** `backend/app/repositories/tenant_repo.py`, `backend/app/audit/repository.py`.

**Affected endpoints:** `GET /api/v1/tenants/current`, `PATCH /api/v1/tenants/current`, `GET /api/v1/audit-events` — all three are ordinary tenant-role endpoints (`CAN_READ_DASHBOARD`/`CAN_MANAGE_TEAM`/`CAN_READ_AUDIT`), not platform-admin-gated.

**Why RLS-only was not enough in local/dev/demo:** `tenants` and `audit_events` are, by migration design (`migrations/versions/0002_core_tenancy.py`, `0003_audit_events.py`), the two tables that rely purely on a Postgres RLS policy rather than an app-level `tenant_id`/`id` filter in code — unlike every other repository in the codebase, which filters explicitly in addition to RLS. This is safe only when the connecting DB role enforces RLS. Prior evidence (P3-2 live DB smoke) documented that the local/dev `app_user` role runs as `SUPERUSER`/`BYPASSRLS`, under which Postgres silently ignores forced RLS policies. Under that condition:

- `TenantRepository.get_current_tenant()` ran `SELECT ... FROM tenants` with no `WHERE` clause — with 2+ tenant rows present, `.mappings().first()` would return an arbitrary tenant's row, not necessarily the caller's own (silent cross-tenant read).
- `TenantRepository.update_current_tenant()` ran `UPDATE tenants SET ... RETURNING ...` with no `WHERE` clause — with 2+ tenant rows present, the `UPDATE` itself would apply to every row in the table before `.mappings().one()` raised `MultipleResultsFound` on the multi-row `RETURNING` result. The mutation happens before the exception surfaces, so this was not a silently-swallowed error — it was actual cross-tenant data corruption surfaced as a 500.
- `AuditRepository.list_recent_bounded()` (including its cursor-lookup sub-query) ran `SELECT ... FROM audit_events` with no `tenant_id` filter — any tenant user calling `GET /api/v1/audit-events` could read every other tenant's audit log under a bypassed-RLS connection.

With only one demo tenant present in most local runs, none of this was visible in the existing E2E/stability smoke output — it required multiple tenant rows to manifest, which is exactly the "not covered until you look" gap this slice closes.

**Why the production boot guard reduces but does not remove the need for app-level scoping:** `backend/app/observability/boot_guard.py`'s `ROLE_SAFETY_SQL` check fails `APP_ENV=production` boot if the connecting role is `SUPERUSER`/`BYPASSRLS`, so a correctly configured production deploy should never hit this condition. However: (a) the guard does not gate `local`/`development`/`demo` environments, where `BYPASSRLS` is a documented current fact, not a hypothetical; (b) CLAUDE.md rule 6 and the repo's own stated philosophy ("RLS is the final guardrail, not the only guardrail") require app-level checks regardless of environment, so a boot-guard-only defense would still leave a single point of failure (a policy misconfiguration, a missed `FORCE ROW LEVEL SECURITY`, or a future role change) with zero secondary check. Every other repository in the codebase already carries this same defense-in-depth pattern; `tenant_repo.py` and `audit/repository.py` were the two outliers.

## Fix summary

- `TenantRepository.get_current_tenant(*, tenant_id)` and `update_current_tenant(*, tenant_id, ...)` now take an explicit `tenant_id: uuid.UUID` and filter `.where(Tenant.id == tenant_id)` (get) / `.where(Tenant.id == tenant_id)` before `.values(...)` (update) — matching the same explicit-filter convention used by every other repository (e.g. `campaign_repo.py`, `draft_repo.py`).
- `AuditRepository.list_recent_bounded(*, tenant_id, cursor, limit)` now filters `.where(AuditEvent.tenant_id == tenant_id)` on both the main query and the cursor-lookup sub-query (the cursor peek query was previously unfiltered too).
- Tenant source used: `principal.tenant_id` — the authenticated, session-bound tenant id already available in `SettingsAPIService` from `CurrentPrincipal` (set by Clerk/local-mock auth + tenant context, never caller-suppliable). `SettingsAPIService.get_current_tenant`, `update_current_tenant_idempotent`, and `list_audit_events` now thread `principal.tenant_id` down to the repository call in each case.
- `TenantSettingsStore` and `AuditReadStore` Protocol definitions in `backend/app/services/settings_api.py` updated to require `tenant_id` as a keyword-only argument, so any future implementation of these protocols cannot omit the filter without a type error.
- `backend/app/scripts/bootstrap_local_demo.py`'s existing call site updated to pass `tenant_id=tenant_id` (the well-known local demo tenant id) — this also makes the idempotent existence check strictly correct (it previously checked "does any tenant exist", not "does the demo tenant exist").
- API response shapes, RBAC permission checks (`CAN_READ_DASHBOARD`, `CAN_MANAGE_TEAM`, `CAN_READ_AUDIT`), idempotency behavior, and audit-record emission are all unchanged — only the repository query scoping changed.
- RLS remains fully in place and required; this fix does not touch, weaken, or replace any RLS policy or the boot guard — it adds an independent, redundant check.
- Route → service → repository layering is preserved; no route handler makes a direct DB call.

## Deferred follow-ups (not fixed in this slice — documented, not live risk)

- **`TenantRepository.get_current()`** — still unused (zero callers repo-wide, confirmed again in this slice); still self-documents as unfiltered/deferred. Left as-is; a landmine only if wired up later without adding a filter.
- **`CredentialRepository.get_by_type()`** — still has zero callers repo-wide despite the table's `UNIQUE(tenant_id, credential_type)` constraint implying multi-tenant rows can share a `credential_type`. Not fixed here since it is dead code with no live route; flagged for whoever wires it up next to add a `tenant_id` filter at that time.
- **`followup_scheduler.py:770-792` inline DB access** — the inline `ContactStoreImpl` class queries `Contact` directly inside a service method instead of through a repository (CLAUDE.md rule 5 layering note). It already correctly filters by `tenant_id`, so it is not a safety bug, only an architecture/layering inconsistency. Deferred as a separate refactor since it carries no tenant-isolation risk today and touching it was out of scope for this safety-focused slice.
- No other missing-tenant-filter repository methods were found in this slice (matches the P4-RepositoryRowMapping-Hardening sweep's earlier conclusion that these three were the only remaining gaps).

## Tests added/updated

All in `backend/tests/` (unit-level, fake-connection style matching existing repository test conventions — no real Postgres needed; real-stack verification is via the Docker E2E/stability scripts below).

`backend/tests/test_repository_row_mapping.py`:
- `test_audit_repository_list_recent_bounded_filters_by_tenant_id` — proves the generated SQL for `list_recent_bounded` carries a `WHERE` clause referencing `audit_events.tenant_id` bound to the given tenant id.
- `test_audit_repository_list_recent_bounded_scopes_to_given_tenant_not_hardcoded` — proves the bound filter value tracks whichever `tenant_id` argument is passed in (not a hardcoded constant).
- `test_tenant_repository_get_current_tenant_filters_by_tenant_id` — same proof for `get_current_tenant`'s `WHERE tenants.id = ...`.
- `test_tenant_repository_get_current_tenant_scopes_to_given_tenant_not_hardcoded` — same "tracks the argument" proof for the read path.
- `test_tenant_repository_update_current_tenant_filters_by_tenant_id` — same proof for `update_current_tenant`'s `WHERE tenants.id = ...`.
- `test_tenant_repository_update_current_tenant_does_not_target_other_tenant` — proves an update scoped to tenant A never carries tenant B's id among its bound WHERE parameters, i.e. it structurally cannot target another tenant's row.
- 3 pre-existing repository tests updated to pass the now-required `tenant_id` keyword argument.

`backend/tests/test_router_settings.py`:
- `test_service_update_scopes_repository_call_to_principal_tenant` — proves `SettingsAPIService` always passes `principal.tenant_id` down to the tenant store on both read and update, never a different value.
- `test_service_list_audit_events_scopes_repository_call_to_principal_tenant` — same proof for the audit-events path.
- `_TenantStore`/`_AuditStore` test fakes updated to require and record `tenant_id`, so a regression that stops threading `tenant_id` through the service fails immediately with a `TypeError` at the fake-protocol boundary, not silently.

`backend/tests/test_bootstrap_local_demo.py`:
- `_FakeTenantRepo.get_current_tenant` updated to require `tenant_id` and to return `None` when the fake's stored tenant id does not match, so the existing bootstrap idempotency tests also exercise (and would catch a regression in) the corrected "does the demo tenant specifically exist" check.

Each new test was written and confirmed to fail with `TypeError: ... got an unexpected keyword argument 'tenant_id'` (or `missing 1 required keyword-only argument`) against the pre-fix source before the repository/service/script changes were made, per TDD.

## Gate results

**Backend:**

| Gate | Result |
|---|---|
| `ruff check app tests` | All checks passed |
| `black --check app tests` | All done — 225 files unchanged |
| `mypy app --ignore-missing-imports` | Success: no issues found in 161 source files |
| `pytest -q` | 824 passed, 0 failed (816 pre-existing + 8 new) |

**Frontend** (run for confidence only — no frontend files staged/changed in this slice):

| Gate | Result |
|---|---|
| `npm run lint` | No ESLint warnings or errors |
| `npm run typecheck` | Clean (`tsc --noEmit`, no output) |
| `npm run test -- --run` | 142 passed (4 test files) |
| `npm run build` | Compiled successfully, 27 routes generated |

**Docker verification:**

| Step | Result |
|---|---|
| `docker compose down --remove-orphans` | Clean teardown, all 5 containers/network removed |
| `docker compose up -d --build` | Clean rebuild, all 5 services created and started |
| `docker compose ps` | db (healthy), backend, frontend, worker, n8n all Up |
| `GET /health` | 200 `{"status":"ok"}` |
| `GET /live` | 200 `{"status":"alive","service":"backend"}` |
| `GET /ready` | 200 `{"status":"ok","environment":"local","checks":{"database":"ok","migrations":"up_to_date","rate_limit_backend":"in_memory"}}` |
| `local_e2e_smoke` | `SMOKE PASSED (16/16)`, including `audit_trail` and full review/send/audit path against the now-tenant-scoped queries |
| `local_stability_smoke` | `STABILITY PASSED (passes=77 failures=0 requests=188 server_500s=0 exceptions=0 clean_failures=2 e2e_runs=4)` — identical to the P4-LocalLoadStabilitySmoke baseline, confirming zero regression |

## Safety confirmation

- No live email was sent.
- No Resend live send occurred.
- No cold outreach live send occurred.
- No Stripe money movement occurred.
- No production mode was enabled.
- No AWS provisioning occurred.
- No registry push occurred.
- No SMS or live scraping occurred.
- `p4/next15-upgrade` was not merged (reconfirmed via `git merge-base --is-ancestor` before and after this slice).
- No frontend action/integration work was done in this slice — `frontend/components/public/auth-card.tsx` had a pre-existing uncommitted change (unrelated small UX fix wrapping the sign-in button in a `<form onSubmit>`) present in the working tree before this slice started; it was left untouched, not staged, and not committed as part of this change.
- No package/lockfile changes, no `.env` changes, no secrets added, no n8n workflow JSON added.
- RLS was not weakened, disabled, or bypassed anywhere; the production boot guard was not modified.

## Remaining blockers

- Frontend readiness/action E2E still needs its own audit/completion pass — explicitly out of scope here.
- `npm audit` on `master` remains pending `p4/next15-upgrade` owner approval/merge (unchanged by this slice).
- Staging remains paused.
- Production still waits for the first real client.
- The uncommitted `frontend/components/public/auth-card.tsx` change remains outside version control — flagged for the owner to commit or discard separately.

## Final verdict

- **P4-RLSDefenseInDepth-Fix: complete.**
- **Tenant/audit explicit scoping: fixed** — `tenant_repo.py` and `audit/repository.py` both now filter explicitly in addition to RLS.
- **Frontend action E2E: still unaudited** (unchanged, out of scope for this slice).
- **Boss demo: allowed** (local/mock demo verified green end-to-end after this fix).
- **Staging: paused.**
- **Production: waits for first real client.**
- **`p4/next15-upgrade`: not merged.**
