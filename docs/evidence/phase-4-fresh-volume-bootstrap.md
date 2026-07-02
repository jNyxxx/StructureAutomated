# P4-FreshVolumeBootstrap

**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `b419bd0 fix(auth): allow local mock logout and re-login`
**Status:** COMPLETE. A brand-new, empty local Docker Postgres volume can now reach the full grounded happy-path E2E flow through two committed, idempotent scripts — no manual SQL required.

## Scope

Local-only. Adds one new backend script, four small repository additions it depends on, and unit tests. No staging/production/live-provider changes, no `p4/next15-upgrade` merge, no package/dependency changes, no real `.env` changes, no Docker image/compose structural changes.

## Fresh-volume gap

`docs/evidence/phase-4-local-docker-e2e-fix-4-grounded-happy-path-seed.md` (Remaining blockers) flagged this explicitly:

```text
Fresh-volume tenant bootstrap: The seed's tenant precondition depends on the
tenant/user/membership rows manually provisioned in P3-2
(docs/evidence/phase-3-2-live-db-smoke.md); those rows live only in the
current automatedstructure_db_data Docker volume, not in a committed
migration/seed. On a fresh volume (docker compose down -v), the seed script
fails closed with an actionable SeedPreconditionError pointing at the P3-2
doc rather than silently succeeding or crashing.
```

Why it mattered: `docker compose exec backend python -m app.scripts.seed_local_grounding` (the grounding data needed for draft generation to reach `generated` instead of `needs_regeneration`) hard-depends on a tenant/user/membership/subscription row set that was only ever created once, by hand, via raw SQL during P3-2 (`docs/evidence/phase-3-2-live-db-smoke.md:76-88`). Anyone tearing down the Docker volume (`docker compose down -v`) or spinning up a new machine had no committed path back to a working demo — only a doc pointing at manual SQL to re-run.

## Fix/bootstrap summary

| File | Change |
|---|---|
| `backend/app/scripts/bootstrap_local_demo.py` | New. Idempotently provisions the demo tenant, owner user, membership, `mvp_mock` billing plan + active subscription, and a safe compliance profile — mirroring `seed_local_grounding.py`'s env-guard/pure-core/`tenant_session`-wrapped/CLI structure exactly. |
| `backend/app/repositories/tenant_repo.py` | Added `create(id, name)`. |
| `backend/app/repositories/user_repo.py` | Added `create(id, email, identity_provider, provider_user_id)`. |
| `backend/app/repositories/membership_repo.py` | Added `create(tenant_id, user_id, role)`. |
| `backend/app/repositories/billing_repo.py` | Added `get_plan_by_key(key)` lookup (existence check before `create_plan`, which is not itself idempotent). |
| `backend/tests/test_bootstrap_local_demo.py` | New. Fake-repo unit tests (env guard, first-run creation, idempotent rerun, partial-state completion). |

Local/demo guards:

- Refuses to run unless `APP_ENV` is `local`/`development`/`demo` (`ensure_bootstrap_env_allowed`, same allowlist shape as `seed_local_grounding.ensure_seed_env_allowed`).
- Uses the same fixed demo identity the mock-auth verifier and grounding seed already hardcode: tenant `22222222-2222-2222-2222-222222222222`, user `11111111-1111-1111-1111-111111111111`, email `owner@example.com`, role `owner` — no new IDs, nothing to keep in sync elsewhere.
- Compliance profile defaults: `sending_review_required=True`, `live_sending_allowed=False`, `sms_allowed=False`.
- Billing state: same `mvp_mock`/`active` mock plan already reviewed in P3-2. No real Stripe involvement.

Idempotency behavior: every entity is checked (via an existing repository read method) before insert. On this specific fresh volume, `plans.mvp_mock` was already present (seeded by migration `0009_mock_billing`), so `get_plan_by_key` correctly skipped plan creation on the very first run — proving the existence check, not just the "second run", is load-bearing. Running the script twice in a row on the same DB produces `CREATED` once per entity and `SKIPPED (already_exists)` on every entity on the second run, with zero duplicate-key errors.

Why safety gates are preserved: every write goes through `tenant_session(tenant_id=..., actor_id=...)` — the same tenant-scoped connection helper every router/service uses (`backend/app/database.py`). No raw connections, no RLS bypass. Tenant/membership/subscription/compliance inserts all carry `tenant_id` equal to the session's GUC, satisfying each table's forced-RLS `WITH CHECK`. No billing gate, send gate, groundedness gate, or human-approval gate is touched or weakened — this script only provisions the tenant's own initial state, the same category of action the original manual P3-2 SQL performed.

Deliberate scope limit: the script does not write `audit_events` rows (there's no existing tenant-onboarding service to hook into, and this is one-time local infrastructure provisioning, not a user action). The script's own stdout output and this evidence doc are the record, matching how the original manual SQL worked.

## Tests added/updated

`backend/tests/test_bootstrap_local_demo.py` (6 tests):

- `test_bootstrap_refuses_non_local_envs` — staging/production/unknown all raise `BootstrapEnvironmentError`.
- `test_bootstrap_allows_local_mock_envs` — local/development/demo all pass.
- `test_bootstrap_creates_all_entities_on_first_run` — fresh fakes → tenant/user/membership/plan/subscription all created; membership role is `owner`; subscription is `active`/`mvp_mock`; compliance profile has live sending and SMS off.
- `test_bootstrap_is_idempotent` — running the core function twice against the same fakes yields zero re-creates on the second pass (create-call counters stay at 1 each); compliance `upsert_profile` is called twice by design (it's already idempotent).
- `test_bootstrap_partial_state_is_completed_not_duplicated` — pre-seeded tenant+user, empty membership/billing/compliance → only the missing entities get created, existing tenant/user are left alone.
- `test_bootstrap_default_identity_matches_mock_auth` — pins `DEFAULT_TENANT_ID`/`DEFAULT_USER_ID` to the values `app/auth/local_mock.py` and `seed_local_grounding.py` already hardcode.

## Gate results

Backend gates:

| Gate | Result |
|---|---|
| `python -m ruff check app tests` | PASS |
| `python -m black --check app tests` | PASS — 221 files unchanged |
| `python -m mypy app --ignore-missing-imports` | PASS — 159 source files |
| `python -m pytest -q` | PASS — 800 tests (794 prior + 6 new bootstrap tests) |

Frontend gates (no frontend files changed; run for completeness):

| Gate | Result |
|---|---|
| `npm run lint` | PASS — no ESLint warnings/errors |
| `npm run typecheck` | PASS |
| `npm run test` | PASS — 142 tests |
| `npm run build` | PASS — 27 routes |

Isolated fresh-volume Docker verification (`COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke`, distinct from the normal `automatedstructure` project/volume):

| Step | Result |
|---|---|
| `docker compose down --remove-orphans` (normal stack, stopped to free host ports; volume preserved) | PASS |
| `COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose up -d --build` | PASS — new `automatedstructure_fresh_smoke_db_data` volume created |
| `docker compose ps` | PASS — db healthy; backend/frontend/n8n/worker up |
| `alembic upgrade head` | PASS — full chain `0001_extensions` → `00022_platform_admin_role` applied to the empty volume |
| `python -m app.scripts.bootstrap_local_demo` (1st run) | PASS — `tenant: CREATED`, `user: CREATED`, `membership: CREATED`, `billing_plan: SKIPPED (already_exists)`, `billing_subscription: CREATED` |
| `python -m app.scripts.bootstrap_local_demo` (2nd run) | PASS — all five entities `SKIPPED (already_exists)` |
| `python -m app.scripts.seed_local_grounding` | PASS — `SEEDED: ... chunk_count=2` (previously would fail with `SeedPreconditionError` on a fresh volume) |
| `GET /health` | PASS — `{"status":"ok"}` |
| `GET /live` | PASS — `{"status":"alive","service":"backend"}` |
| `GET /ready` | PASS — `database: ok`, `migrations: up_to_date`, `rate_limit_backend: in_memory` |

Abbreviated fresh-volume E2E result (all via HTTP against the isolated stack, `Authorization: Bearer token-sentinel` + `X-Tenant-ID: 22222222-2222-2222-2222-222222222222`):

| Step | Result |
|---|---|
| `GET /api/v1/tenants/current` | PASS — returns the bootstrap-created tenant |
| `POST /api/v1/imports/contacts` | PASS — `status: completed`, 1 valid row |
| `POST /api/v1/campaigns` | PASS — campaign created, `status: draft` |
| `POST /api/v1/campaigns/{id}/contacts` | PASS — contact selected |
| `POST /api/v1/drafts/generate` | PASS — `status: "generated"` (not `needs_regeneration`) |
| `GET /api/v1/review/items` | PASS — item `pending_review` |
| `POST /api/v1/review/items/{id}/approve` | PASS — `status: approved` |
| `POST /api/v1/send-gate/dry-run` | PASS — `status: "passed"`, `mock_only: true` |
| `POST /api/v1/send-intents` | PASS — `status: "mock_sent"`, `mock_only: true` |
| `GET /api/v1/outbound-messages` | PASS — mock-sent message present |
| `GET /api/v1/audit-events` | PASS — full 11-event trail from `contact_import.completed` through `outbound_message.sent`, all safety/groundedness/send-gate events `passed` |
| Teardown: `COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose down -v --remove-orphans` | PASS — disposable volume removed |
| Restore: `docker compose up -d --build` (normal project) | PASS — original `automatedstructure_db_data`/`automatedstructure_n8n_data` volumes untouched throughout |

## Safety confirmation

- No real email was sent.
- No Resend live send occurred.
- No cold outreach live send occurred.
- No Stripe checkout, billing portal, webhook, billing-state mutation, or money movement occurred (mock `mvp_mock` plan only).
- No production mode was enabled (`APP_ENV=local` throughout).
- No AWS provisioning occurred.
- No registry push occurred.
- No deployment occurred.
- No SMS or live scraping occurred.
- `p4/next15-upgrade` was not merged.
- No package/dependency/lockfile changes.
- No real `.env` file changes.
- No RLS/tenant-context/RBAC gate weakened — all writes went through `tenant_session()`.
- No billing/send/groundedness/human-approval gate bypassed.
- The normal dev stack's Docker volume (`automatedstructure_db_data`) was never deleted or written to by the fresh-volume smoke test; isolation was achieved entirely via `COMPOSE_PROJECT_NAME`.

## Remaining blockers

| Item | Status |
|---|---|
| `npm audit` on `master` | Still blocked until `p4/next15-upgrade` is approved/merged or risk is accepted. |
| Staging | Paused. |
| Production | Waits for first real client and separate owner/operator approvals. |
| Real providers | Disabled. Resend/Stripe remain non-live. |
| Local fresh-volume bootstrap | **Resolved by this slice** — no manual SQL step remains. |

## Final verdict

- P4-FreshVolumeBootstrap: **COMPLETE**.
- Fresh local Docker bootstrap: **works** — `alembic upgrade head` → `bootstrap_local_demo` → `seed_local_grounding` reaches a fully working grounded happy path on an empty volume, no manual step required.
- Boss demo: **allowed** (local/mock flow, unaffected — normal dev volume was preserved and restored).
- Staging: **paused**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
