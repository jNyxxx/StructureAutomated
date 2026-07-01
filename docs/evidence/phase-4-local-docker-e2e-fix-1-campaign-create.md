# P4-LocalDockerE2E-Fix-1-CampaignCreate — Campaign Create Write-Path Fix

**Purpose:** Fix the local Docker `POST /api/v1/campaigns` 500 and resume the local happy-path E2E as far as this slice safely allows.
**Slice:** P4-LocalDockerE2E-Fix-1-CampaignCreate
**Date:** 2026-07-01
**Branch:** `master`
**Base commit:** `eb51a29 docs(p4): add local Docker E2E verification`
**Status:** PARTIAL COMPLETE — campaign create is fixed and verified; full happy-path E2E is still blocked by the next write-path repository mapper issue in contact import.

---

## 1. Scope and boundaries

This slice was local-only.

Preserved hard stops:

- `p4/next15-upgrade` was **not** merged.
- No package changes.
- No `npm audit fix` or `npm audit fix --force`.
- No real `.env` edits.
- No secrets added.
- No AWS provisioning.
- No deployment.
- No registry push.
- No staging enablement.
- No production enablement.
- No live providers enabled.
- No Resend/live send.
- No cold outreach live send.
- No Stripe money movement.
- No SMS/live scraping.
- No auth/RBAC/RLS/tenant isolation weakening.
- No billing/send-gate/idempotency bypass.
- No DB calls were moved into route handlers.
- Server-side gates remain authoritative.

---

## 2. Bug summary

Original endpoint:

```text
POST /api/v1/campaigns
```

Original Docker backend failure:

```text
backend/app/repositories/campaign_repo.py line 73
return _campaign(row)

backend/app/repositories/campaign_repo.py line 18
id=row.id

AttributeError: 'asyncpg.pgproto.pgproto.UUID' object has no attribute 'id'
```

Root cause:

- `CampaignRepository.create_campaign()` used `insert(Campaign).returning(Campaign)` with `AsyncConnection`.
- It then called `.scalars().one()`.
- In this runtime path, `.scalars().one()` returned the first scalar column, the campaign UUID, not a campaign row/object.
- `_campaign(row)` expected a full row with fields such as `id`, `tenant_id`, `created_by_user_id`, `name`, and `status`.
- Passing a scalar UUID into `_campaign(row)` caused the 500.

Why it blocked E2E:

- Campaign creation is the first real backend write path in the local Docker happy-path demo.
- Draft generation, review, send-gate dry run, mock send intent, outbound messages, and audit trail depend on having a valid campaign/contact/draft chain.

---

## 3. Fix summary

Files changed:

| File | Change |
|---|---|
| `backend/app/repositories/campaign_repo.py` | Replaced ORM/scalar-style row handling with explicit returned columns and `Result.mappings()` for campaign and campaign-contact repository methods. |
| `backend/app/repositories/idempotency_repo.py` | Fixed the same scalar UUID mapping issue for idempotency lookup, which directly blocked campaign-create idempotency replay. Added `IdempotencyRecord` and explicit-column mapping. |
| `backend/tests/test_campaign.py` | Added regression coverage proving campaign create maps a complete row and fails if the repository falls back to scalar UUID mapping. |
| `backend/tests/test_idempotency.py` | Added regression coverage proving idempotency lookup maps a complete record and fails if it falls back to scalar UUID mapping. |

Repository behavior before:

```text
insert(...).returning(Campaign).scalars().one()
```

This could return only the scalar `id` under `AsyncConnection`.

Repository behavior after:

```text
insert(...).returning(*_CAMPAIGN_COLUMNS)
...
result.mappings().one()
```

and:

```text
select(*_CAMPAIGN_COLUMNS)
...
result.mappings().first()/all()
```

Why tenant/RLS/idempotency behavior is preserved:

- The router still depends on `current_principal`.
- The router still builds `CampaignService` inside `tenant_session(...)`.
- The repository still receives a tenant-scoped connection from `tenant_session`.
- Tenant predicates were preserved in reads/updates/contact selection.
- No direct DB access was added to route handlers.
- Service-layer RBAC, billing, object authorization, audit, and idempotency gates were not bypassed.
- Idempotency behavior was strengthened by fixing full-record lookup instead of bypassing the gate.

---

## 4. Tests added / updated

Added backend regression tests:

| Test | Purpose |
|---|---|
| `test_campaign_repository_create_returns_complete_campaign_without_scalar_mapper` | Verifies campaign create returns a complete `CampaignRecord`, preserves returned id/tenant/actor fields, and fails if `CampaignRepository` uses `.scalars()` instead of row mappings. |
| `test_idempotency_repository_get_returns_complete_record_without_scalar_mapper` | Verifies idempotency lookup returns a complete record with request/response hash and status fields, and fails if the repository uses `.scalars()` instead of row mappings. |

Targeted tests:

| Command | Result |
|---|---|
| `python -m pytest tests/test_campaign.py -q` | PASS — 12 tests |
| `python -m pytest tests/test_idempotency.py -q` | PASS — 9 tests |

---

## 5. Backend gate results

Commands run from `backend/`:

| Gate | Result |
|---|---|
| `python -m ruff check app tests` | PASS |
| `python -m black --check app tests` | PASS — 214 files unchanged after formatting touched files |
| `python -m mypy --ignore-missing-imports app` | PASS — 156 source files checked |
| `python -m pytest -q` | PASS — full backend suite completed; existing Starlette/httpx deprecation warning remains |

Backend verdict: **PASS**.

---

## 6. Frontend gate results

No frontend files changed, but frontend gates were rerun as required.

Commands run from `frontend/`:

| Gate | Result |
|---|---|
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm run test` | PASS — 4 files / 141 tests |
| `npm run build` | PASS — Next 14.2.35 generated 27 static pages |

Expected test stderr remains for network fallback and jsdom navigation behavior. Tests still pass.

Frontend verdict: **PASS**.

---

## 7. Docker compose and health results

Commands:

```text
docker compose down --remove-orphans
docker compose up -d --build
docker compose ps
```

Compose result: **PASS**.

Services after rebuild:

| Service | Status | Port |
|---|---|---|
| `db` | Up / healthy | `5432 -> 5432` |
| `backend` | Up | `8000 -> 8000` |
| `frontend` | Up | `3000 -> 3000` |
| `n8n` | Up | `5678 -> 5678` |
| `worker` | Up | placeholder |

Backend health after rebuild:

| Endpoint | Result | Response |
|---|---|---|
| `GET /ready` | PASS | `status=ok`, `database=ok`, `migrations=up_to_date`, `rate_limit_backend=in_memory` |
| `GET /health` | PASS | `{"status":"ok"}` |
| `GET /live` | PASS | `{"status":"alive","service":"backend"}` |

---

## 8. Campaign create verification

Docker backend campaign-create verification:

| Check | Result |
|---|---|
| `POST /api/v1/campaigns` with local mock auth token, demo tenant header, idempotency key, and JSON body | PASS — HTTP 201 |
| `GET /api/v1/campaigns` with local mock auth token and demo tenant header | PASS — HTTP 200 |
| Campaign list response includes complete campaign objects | PASS — returned objects include `id`, `created_by_user_id`, `name`, `description`, `goal`, `target_segment`, `notes`, and `status`. |

Observed campaign list response included complete rows such as:

```text
{
  "id": "f7ed5777-a5f5-4d47-8add-1aa8186d6847",
  "created_by_user_id": "11111111-1111-1111-1111-111111111111",
  "name": "Docker E2E",
  "description": null,
  "goal": null,
  "target_segment": null,
  "notes": null,
  "status": "draft"
}
```

Campaign-create verdict: **FIXED**.

---

## 9. Frontend Docker route smoke

Route smoke through the running compose frontend on `http://localhost:3000`:

| Route | Status | Result |
|---|---:|---|
| `/login` | 200 | PASS |
| `/dashboard` | 200 | PASS |
| `/prospects` | 200 | PASS |
| `/campaigns` | 200 | PASS |
| `/campaigns/new` | 200 | PASS |
| `/ai-drafts` | 200 | PASS |
| `/review-queue` | 200 | PASS |
| `/deliverability` | 200 | PASS |
| `/outcomes` | 200 | PASS |
| `/audit-logs` | 200 | PASS |
| `/billing` | 200 | PASS |
| `/settings/compliance` | 200 | PASS |
| `/settings/suppression` | 200 | PASS |
| `/settings/team` | 200 | PASS |

Frontend Docker route-smoke verdict: **PASS**.

---

## 10. Resumed happy-path E2E result

Result: **PARTIAL / STILL BLOCKED AFTER CAMPAIGN CREATE**.

| Flow | Result | Notes |
|---|---|---|
| Login page loads | PASS | `/login` route smoke 200. |
| Demo login works | PARTIAL | Local mock auth API smoke worked in prior retry; full browser click-through not completed by shell tool. |
| Dashboard loads | PASS | `/dashboard` 200. |
| Campaign create works | **PASS** | Docker backend `POST /api/v1/campaigns` now returns 201. |
| Campaign appears in list | **PASS** | Docker backend `GET /api/v1/campaigns` returns complete campaign objects. |
| Contact/prospect import | **BLOCKED** | `POST /api/v1/imports/contacts` now reaches backend but returns 500 from `contact_repo.py` scalar UUID row mapping. |
| Draft/evidence/review queue happy path | BLOCKED | Needs valid contact/import path. Routes still load. |
| Human approval path visible | PARTIAL | Route loads; valid draft chain not reached. |
| Send-gate dry run happy path | BLOCKED | Needs valid approved draft. Fail-closed behavior remains tested. |
| Mock send intent happy path | BLOCKED | Needs valid approved draft. |
| Outbound/audit trail | PARTIAL | Routes load; full action chain not completed. |
| Billing/access UI | PASS | `/billing` 200. |
| Compliance/suppression UI | PASS | routes 200. |
| No real provider action occurs | PASS | No provider/staging/production work occurred. |

New blocker found after campaign fix:

```text
POST /api/v1/imports/contacts -> 500
backend/app/repositories/contact_repo.py line 179
return _import(row)
backend/app/repositories/contact_repo.py line 39
id=row.id
AttributeError: 'asyncpg.pgproto.pgproto.UUID' object has no attribute 'id'
```

Interpretation:

- The original campaign-create blocker is fixed.
- The happy path now advances to the next local backend write path and hits the same `AsyncConnection` scalar-row-mapping class in `ContactImportRepository`.
- This should be handled in a separate slice instead of broadening this campaign-create fix further.

---

## 11. Safety confirmation

| Safety item | Result |
|---|---|
| Real email sent | NO |
| Resend live send | NOT ENABLED |
| Cold outreach live send | NOT ENABLED |
| Stripe money movement | NOT ENABLED |
| Production mode | NOT ENABLED |
| Staging mode | NOT ENABLED |
| AWS provisioning | NOT PERFORMED |
| Registry push | NOT PERFORMED |
| Deployment | NOT PERFORMED |
| SMS/live scraping | NOT ENABLED |
| Real secrets added | NO |
| Real `.env` edited | NO |
| Auth/RBAC/RLS/tenant isolation weakened | NO |
| Billing/send gates bypassed | NO |
| Idempotency bypassed | NO — idempotency lookup was fixed, not skipped |
| Frontend-only gate trust introduced | NO |
| `p4/next15-upgrade` merged | NO |

---

## 12. Remaining blockers

| Blocker | Status | Required next action |
|---|---|---|
| Contact import write path | BLOCKED | Open a separate source-fix slice for `ContactImportRepository` / `contact_repo.py` row mapping. |
| Full campaign/contact/draft/review/send happy path | BLOCKED | Depends on contact import fix, then possible further repository write-path checks. |
| Manual browser click-through | CAVEATED | Re-run after contact import and downstream write paths pass. |
| `npm audit` on `master` | BLOCKED | Clean fix exists on `p4/next15-upgrade`; merge only when William approves. |
| `p4/next15-upgrade` | WAITING OWNER APPROVAL | Not merged in this slice. |
| Staging | PAUSED BY WILLIAM | Do not resume until owner signal. |
| AWS/deployment/registry/provider setup | PAUSED BY WILLIAM | Do not configure or request values yet. |
| Production | WAITING FIRST REAL CLIENT | No production work yet. |

---

## 13. Recommendation

Recommendation:

1. Treat `P4-LocalDockerE2E-Fix-1-CampaignCreate` as complete for the campaign-create blocker.
2. Do not claim full local Docker happy-path E2E yet.
3. Open the next source-fix slice:

```text
P4-LocalDockerE2E-Fix-2-ContactImport
```

Suggested scope:

- inspect `backend/app/repositories/contact_repo.py`;
- fix `ContactImportRepository` and related contact/import row mappers to use explicit columns + `Result.mappings()` instead of `.scalars()` where needed;
- add regression tests like this slice did;
- rerun backend/frontend/Docker checks;
- retry contact import, contact list, campaign contact selection, draft generation, review, send-gate dry run, mock send intent, outbound/audit.

Boss demo status:

- Campaign-create demo path is fixed.
- Boss demo remains allowed only with caveats until contact import and the downstream happy path pass.

---

## 14. Final verdict

- P4-LocalDockerE2E-Fix-1-CampaignCreate: **PARTIAL COMPLETE**.
- Campaign create: **FIXED**.
- Idempotency replay lookup for campaign create: **FIXED**.
- Local Docker campaign create/list E2E: **PASS**.
- Full local Docker happy-path E2E: **STILL BLOCKED** by contact import row mapping.
- Boss demo: **allowed only with caveats**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
