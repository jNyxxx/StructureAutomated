# P4-RepositoryRowMapping-Hardening

**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `6a6c8eb test(p4): add grounded local happy-path coverage`
**Status:** COMPLETE. Repo-wide sweep for the "scalar RETURNING under AsyncConnection" row-mapping bug class. 9 previously-unfixed repository files hardened; 2 files confirmed already safe; 2 dead-code methods documented and left untouched.

## Scope

Local-only backend hardening and evidence update. `p4/next15-upgrade` was not merged. No package, real `.env`, secret, AWS, registry, deployment, staging, production, provider, Stripe, SMS, or scraping work was performed. Auth/RBAC/RLS/tenant isolation, billing gates, idempotency, and object-authorization behavior were preserved exactly — every fix only changes how a `RETURNING`/`SELECT` result row is read back, never a query predicate, permission check, or gate.

## Background

Fix-4 (previous slice, `6a6c8eb`) discovered that `sending_repo.py` and `audit/repository.py` still had the row-mapping bug already fixed once for `draft_repo.py`/`safety_repo.py`/`review_repo.py`/`campaign_repo.py`/`contact_repo.py` in fix-1/2/3 — and it only surfaced when the send-gate and audit-read paths were exercised in Docker for the first time. This slice does a final repo-wide sweep so no remaining instance of this bug class can ambush a future E2E slice the same way.

Root cause: `BaseRepository.conn` (`backend/app/repositories/base.py`) is a raw `AsyncConnection`, not an ORM `Session`. `insert(Model)...returning(Model)` or `select(Model)` read back via `.scalars().one()/.first()/.all()` does not ORM-hydrate — `.scalars()` returns only column index 0 (typically `id`) as a bare `asyncpg.pgproto.pgproto.UUID`, and mapper functions doing `row.column_name` crash with `AttributeError`. Fix: explicit `_XXX_COLUMNS = (Model.col, ...)` tuple, `select(*_COLUMNS)`/`.returning(*_COLUMNS)`, `.mappings().one()/.first()/.all()`, mapper reads `row["column_name"]`.

## Scan summary

**Files scanned:** every file in `backend/app/repositories/` plus `backend/app/audit/repository.py` (24 files total).

**Already fixed (fix-1/2/3/4, skipped this pass):** `draft_repo.py`, `safety_repo.py`, `review_repo.py`, `knowledge_repo.py`, `sending_repo.py`, `audit/repository.py`, `campaign_repo.py`, `contact_repo.py`.

**Risky patterns found and fixed (9 files, 46 call sites):**

| File | Methods fixed |
|---|---|
| `billing_repo.py` | `set_status`, `create_plan`, `create_subscription` (5 sites incl. 2 nested `Plan` lookups) |
| `compliance_repo.py` | `get_profile`, `upsert_profile` (insert + update branches), `get_active_suppression`, `get_suppression`, `list_suppressions` (cursor pagination), `add_suppression`, `revoke_suppression` (9 sites) |
| `support_access_repo.py` | `create`, `get_active`, `revoke` (3 sites) |
| `membership_repo.py` | `list_memberships`, `get_for_user_and_tenant` (2 sites) |
| `user_repo.py` | `get_by_identity` (1 site) |
| `tenant_repo.py` | `get_current_tenant`, `update_current_tenant` (2 sites) |
| `followup_repo.py` | `create_followup_rule`, `list_followup_rules` (cursor), `get_followup_rule_by_campaign`, `create_followup_schedule`, `get_followup_schedule`, `get_followup_schedule_by_original_message`, `list_followup_schedules` (cursor), `update_followup_schedule_status` (10 sites) |
| `outcomes_repo.py` | `get_outcome_event`, `_get_by_idempotency_key`, `get_roi_assumptions` (3 sites) |
| `research_repo.py` | `create_run`, `get_run`, `update_run`, `increment_run_counts`, `create_artifact`, `get_artifact`, `list_artifacts`, `get_contact` (8 sites) |

**Two findings were more severe than routine mechanical fixes:**

1. **`membership_repo.py::get_for_user_and_tenant` and `user_repo.py::get_by_identity`** are wired directly into the **real (non-mock) Clerk auth path** (`backend/app/auth/managed.py:48-49` → `backend/app/services/auth.py`). `AuthService` calls `user.deleted_at`/`user.id` and `membership.tenant_status`/`membership.membership_version` directly on their return values. Before this fix, any real Clerk-authenticated request against a tenant with actual user/membership rows would crash immediately. This has been entirely masked in local Docker because the local demo path uses `_LocalMockUsers`/`_LocalMockMemberships` (`backend/app/auth/local_mock.py`), which never touch these repositories. Fixed by having both methods return the exact dataclasses (`AuthUser`, `AuthMembership`) the `AuthUserStore`/`AuthMembershipStore` Protocols and the mock classes already use — `TenantMembership` has no `tenant_status` column, so `get_for_user_and_tenant` now joins to `Tenant` and selects `Tenant.status.label("tenant_status")`.
2. **`research_repo.py::get_contact`** previously had no mapper at all — it returned the raw scalar row directly (`return row`). Its sole caller, `process_research_job` in `backend/app/services/research.py` (the research-job worker's main entrypoint), reads `.email`, `.full_name`, and `.company_name` directly. Every real invocation with an existing contact would have crashed. Fixed by reusing `app.services.csv_import.ContactRecord` (the same shape `contact_repo.py` already returns) with a local explicit-columns mapper.

**Confirmed safe as-is (no change needed):** `outcomes_repo.py::create_outcome_event` and `upsert_roi_assumptions` already use `.returning(Model.col_a, Model.col_b, ...).one()` — explicit columns with **no `.scalars()` call** — and a plain `Row` from `.one()` supports attribute access correctly regardless of connection type; the bug is specifically `.scalars()` discarding all but column 0, which these methods never call. `get_outcome_counts`/`get_outcome_trend` (labeled aggregate selects) are safe the same way. Left untouched.

**Confirmed dead code (documented, left untouched):** `tenant_repo.py::get_current()` and `membership_repo.py::list_for_current_tenant()` — verified via repo-wide grep to have zero callers before and after this change. Both now carry an explicit docstring note that they return raw, attribute-unsafe rows and are deferred if ever wired up.

## Fix summary

Every fix follows the identical, already-proven pattern from `sending_repo.py` (straight CRUD) and `audit/repository.py::list_recent_bounded` (cursor pagination):

```text
.returning(Model).scalars().one()   ->   .returning(*_COLUMNS).mappings().one()
select(Model).scalars().first()     ->   select(*_COLUMNS).mappings().first()
```

Repository/service/router layering, tenant predicates, and RLS assumptions are all preserved exactly — every fixed method still filters by `tenant_id` (or relies on the caller's tenant-scoped connection) exactly as before; only the row-consumption mechanics changed. No idempotency behavior changed: `outcomes_repo.py::_get_by_idempotency_key`'s lookup predicate and found/not-found semantics are untouched — the fix only repairs how a *found* row is read (it previously crashed on every idempotency-replay hit; it now returns the existing record correctly). No billing/send/compliance/safety gate logic changed in any file.

## Tests added/updated

`backend/tests/test_repository_row_mapping.py` extended from 9 to 50 tests (41 new), plus an additive test-harness extension:

- `_MappingListResult` — wraps a `list[dict]` for the "main paginated query" leg of cursor pagination (or an empty list to simulate a "not found" `.first()`/`.mappings()` result).
- `_SequencedRepositoryConnection` — returns a different canned result per sequential `execute()` call, for methods that issue two or more queries per call (billing's nested `Plan` lookup, compliance's `upsert_profile` update branch and cursor-paginated `list_suppressions`, followup's two cursor-paginated list methods).

Both are purely additive — the original `_MappingOnlyResult`/`_FakeRepositoryConnection` and all 9 original tests are unchanged.

New tests (one per fixed method, each asserting the repository never calls `.scalars()` and always returns a fully-populated record via `.mappings()`):

- `test_tenant_repository_get_current_tenant_returns_complete_row`, `test_tenant_repository_update_current_tenant_returns_complete_row`
- `test_support_access_repository_create_returns_complete_grant_row`, `test_support_access_repository_get_active_returns_complete_grant_row`, `test_support_access_repository_revoke_returns_complete_grant_row`
- `test_membership_repository_list_memberships_returns_complete_rows`, `test_membership_repository_get_for_user_and_tenant_returns_auth_membership` (pins the `AuthMembership`/JOIN fix on the real auth path)
- `test_user_repository_get_by_identity_returns_auth_user` (pins the `AuthUser` fix on the real auth path)
- `test_billing_repository_create_plan_returns_complete_plan_row`, `test_billing_repository_set_status_returns_complete_subscription_and_plan`, `test_billing_repository_create_subscription_returns_complete_subscription_and_plan` (latter two exercise the nested-lookup sequenced harness)
- `test_compliance_repository_get_profile_returns_complete_row`, `test_compliance_repository_upsert_profile_insert_branch_returns_complete_row`, `test_compliance_repository_upsert_profile_update_branch_returns_complete_row`, `test_compliance_repository_get_active_suppression_returns_complete_row`, `test_compliance_repository_get_suppression_returns_complete_row`, `test_compliance_repository_list_suppressions_no_cursor_returns_complete_rows`, `test_compliance_repository_list_suppressions_with_cursor_returns_complete_rows`, `test_compliance_repository_add_suppression_returns_complete_row`, `test_compliance_repository_revoke_suppression_returns_complete_row`
- `test_followup_repository_create_rule_returns_complete_row`, `test_followup_repository_list_rules_no_cursor_returns_complete_rows`, `test_followup_repository_list_rules_with_cursor_returns_complete_rows`, `test_followup_repository_get_rule_by_campaign_returns_complete_row`, `test_followup_repository_create_schedule_returns_complete_row`, `test_followup_repository_get_schedule_returns_complete_row`, `test_followup_repository_get_schedule_by_original_message_returns_complete_row`, `test_followup_repository_list_schedules_no_cursor_returns_complete_rows`, `test_followup_repository_list_schedules_with_cursor_returns_complete_rows`, `test_followup_repository_update_schedule_status_returns_complete_row`
- `test_outcomes_repository_get_outcome_event_returns_complete_row`, `test_outcomes_repository_get_by_idempotency_key_returns_complete_row` (pins the idempotency-replay crash fix), `test_outcomes_repository_get_roi_assumptions_returns_complete_row`
- `test_research_repository_create_run_returns_complete_row`, `test_research_repository_get_run_returns_complete_row`, `test_research_repository_update_run_returns_complete_row`, `test_research_repository_increment_run_counts_returns_complete_row`, `test_research_repository_create_artifact_returns_complete_row`, `test_research_repository_get_artifact_returns_complete_row`, `test_research_repository_list_artifacts_returns_complete_rows`, `test_research_repository_get_contact_returns_complete_contact_record` (pins the research-worker crash fix; asserts `.email`, `.full_name`, `.company_name` are correctly populated)

## Gate results

Targeted:

```text
python -m pytest tests/test_repository_row_mapping.py -v
50 passed
```

Backend (full):

| Gate | Result |
|---|---|
| Ruff (`app tests`) | PASS |
| Black check (`app tests`) | PASS |
| mypy (`app --ignore-missing-imports`) | PASS — 158 source files |
| pytest (`-q`) | PASS — 792 tests |

Frontend (no frontend source changed; run per spec for contract-stability confidence):

| Gate | Result |
|---|---|
| lint | PASS |
| typecheck (`tsc --noEmit`) | PASS |
| test (vitest) | PASS — 141 tests |
| build (`next build`) | PASS — 27 static/dynamic routes |

Docker:

| Check | Result |
|---|---|
| `docker compose down --remove-orphans` (no `-v`, volumes preserved) | PASS |
| `docker compose up -d --build` | PASS |
| `docker compose ps` | all services up; `db` healthy |
| `GET /health` | `{"status":"ok"}` |
| `GET /live` | `{"status":"alive","service":"backend"}` |
| `GET /ready` | `{"status":"ok","environment":"local","checks":{"database":"ok","migrations":"up_to_date","rate_limit_backend":"in_memory"}}` |
| Route smoke (`/login`, `/dashboard`, `/prospects`, `/campaigns`, `/ai-drafts`, `/review-queue`, `/audit-logs`, `/billing`, `/settings/compliance`, `/settings/suppression`) | all HTTP 200 |

Live spot-check against real Postgres (beyond unit tests, beyond the required gate list) confirming zero regressions on 5 of the 9 fixed repositories that have simple no-setup GET endpoints:

- `GET /api/v1/billing/subscription` → 200, full plan/subscription object (exercises `billing_repo.get_subscription`, already-safe path, confirms router/service composition around the newly-fixed `billing_repo` methods still works).
- `GET /api/v1/compliance/profile` → 200, full profile object (exercises fixed `compliance_repo.get_profile`).
- `GET /api/v1/suppressions` → 200, empty list with pagination envelope (exercises fixed `compliance_repo.list_suppressions`, no-cursor branch).
- `GET /api/v1/tenants/current` → 200, full tenant object (exercises fixed `tenant_repo.get_current_tenant`).
- `GET /api/v1/memberships` → 200, full membership object (exercises fixed `membership_repo.list_memberships`).

`membership_repo.get_for_user_and_tenant` and `user_repo.get_by_identity` (the real-Clerk-auth-path fixes) cannot be live-exercised in local Docker because local auth uses the mock provider (`_LocalMockUsers`/`_LocalMockMemberships`), which never calls these repositories — their correctness is verified by the two dedicated regression tests instead, which is the expected verification path for this masked bug. `support_access_repo.py`, `followup_repo.py`, `outcomes_repo.py`, and `research_repo.py` have no simple no-setup GET endpoint reachable in this session; unit-test coverage is the verification for those four.

## Safety confirmation

- No live email was sent — no sending path was touched by this slice.
- No Resend live send occurred.
- No cold outreach live send occurred.
- No Stripe money movement occurred.
- No production mode was enabled — `APP_ENV=local` throughout.
- No AWS provisioning occurred.
- No container image was pushed to any registry.
- No SMS or live scraping occurred.
- `p4/next15-upgrade` was **not** merged (verified before and after this slice).
- No auth/RBAC/RLS/tenant-isolation weakening — every fixed query still filters by `tenant_id` (or relies on the tenant-scoped connection) exactly as before; the membership fix *adds* a real `tenant_status` value (via JOIN) where previously a crash occurred, strengthening correctness.
- No billing/send-gate bypass — no gate logic was touched.
- No idempotency-rule change — `outcomes_repo._get_by_idempotency_key`'s predicate and found/not-found semantics are unchanged; only the crash-on-found path was repaired.
- No DB access moved into route handlers — all fixes stayed inside `backend/app/repositories/` and `backend/app/audit/`.

## Remaining blockers

| Item | Status |
|---|---|
| `npm audit` on `master` | Still blocked until William approves/merges `p4/next15-upgrade`. |
| Staging | Paused by William. |
| Production | Waits for first real client. |
| `list_recent()` dead code (`audit/repository.py`, noted in fix-4) | Still unused, still unfixed — zero callers, no attribute-access risk today. |
| `tenant_repo.get_current()` / `membership_repo.list_for_current_tenant()` | Confirmed dead code this slice; documented with deferred-comment, left unfixed. |

No further row-mapping risk is known to remain in `backend/app/repositories/` or `backend/app/audit/`: every file in the directory has now been scanned, and every risky `.scalars()` call site found across the two hardening slices (fix-4 and this one) has been fixed or explicitly documented as safe/deferred.

## Verification before commit

- `git diff --check` — clean.
- `git status --short` — only the files listed below.
- `p4/next15-upgrade` confirmed **not** merged.
- No package/lockfile changes.
- No real `.env` file changes.
- No deployment/provider/production changes.
- Changed docs/source grepped for "production enabled" / "deployed" / "real sending enabled" / "money movement enabled" — no unsafe matches (only this doc's own verification-checklist sentence, describing the check itself).
- Changed docs/source grepped for secret-looking values — no matches.
- No registry push, no deployment.
- Repo-wide grep confirms zero remaining `.scalars()` calls in the 9 fixed files.

## Files changed

| File | Change |
|---|---|
| `backend/app/repositories/tenant_repo.py` | Row-mapping fix (`get_current_tenant`, `update_current_tenant`) + dead-code comment on `get_current`. |
| `backend/app/repositories/support_access_repo.py` | Row-mapping fix (all 3 methods). |
| `backend/app/repositories/membership_repo.py` | Row-mapping fix + auth-path return-type fix (`get_for_user_and_tenant` → `AuthMembership` via JOIN) + dead-code comment on `list_for_current_tenant`. |
| `backend/app/repositories/user_repo.py` | Row-mapping fix + auth-path return-type fix (`get_by_identity` → `AuthUser`, keyword-only signature). |
| `backend/app/repositories/billing_repo.py` | Row-mapping fix (`set_status`, `create_plan`, `create_subscription`). |
| `backend/app/repositories/compliance_repo.py` | Row-mapping fix (all 7 methods incl. cursor pagination). |
| `backend/app/repositories/followup_repo.py` | Row-mapping fix (all 8 methods incl. two cursor-paginated list methods). |
| `backend/app/repositories/outcomes_repo.py` | Row-mapping fix (3 methods); already-safe methods left untouched. |
| `backend/app/repositories/research_repo.py` | Row-mapping fix (7 methods) + `get_contact` mapper fix (returns `ContactRecord`). |
| `backend/tests/test_repository_row_mapping.py` | Harness extension (`_MappingListResult`, `_SequencedRepositoryConnection`) + 41 new regression tests. |
| `docs/PHASE_4_IMPLEMENTATION_PLAN.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`, `docs/DOCUMENTATION_MANIFEST.md` | Tracking updates for this slice. |

## Final verdict

- P4-RepositoryRowMapping-Hardening: **COMPLETE**.
- Row-mapping risks: **closed** across all of `backend/app/repositories/` and `backend/app/audit/` (9 files fixed, 2 confirmed safe, 2 confirmed dead code and documented).
- Boss demo: **allowed**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
