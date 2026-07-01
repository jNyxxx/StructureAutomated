# P4-LocalDockerE2E-Fix-2-ContactImport — Contact Import Write-Path Fix

**Purpose:** Fix the local Docker `POST /api/v1/imports/contacts` 500 and continue the local Docker happy-path E2E.
**Slice:** P4-LocalDockerE2E-Fix-2-ContactImport
**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `349a403 fix(backend): return full campaign after create`
**Status:** PARTIAL COMPLETE — contact import is fixed and verified; full happy-path E2E now advances to draft generation and is blocked by the next repository scalar-mapping pattern in `draft_repo.py`.

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

Endpoint:

```text
POST /api/v1/imports/contacts
```

Known Docker backend failure from the previous slice:

```text
backend/app/repositories/contact_repo.py line 179
return _import(row)

backend/app/repositories/contact_repo.py line 39
id=row.id

AttributeError: 'asyncpg.pgproto.pgproto.UUID' object has no attribute 'id'
```

Root cause:

- `ContactImportRepository.create_import()` used `insert(ContactImport).returning(ContactImport)` and then `.scalars().one()`.
- Under the app's `AsyncConnection` execution path, `.scalars().one()` returned the first scalar column, the UUID, not a complete import row/object.
- `_import(row)` expected a row/object with `id`, `tenant_id`, `idempotency_key`, `status`, and count fields.
- Passing the scalar UUID to `_import(row)` caused the local Docker 500.

Why it blocked E2E:

- Contact import is required before a real local contact/prospect can be selected into a campaign.
- Without contact import, the campaign → contact selection → draft generation → review → send-gate → mock send path cannot complete through the local Docker backend.

---

## 3. Fix summary

Files changed:

| File | Change |
|---|---|
| `backend/app/repositories/contact_repo.py` | Replaced ORM/scalar-style row handling with explicit column sets and `Result.mappings()` for contact import, contact, import-row, and contact-read paths. |
| `backend/tests/test_csv_import.py` | Added repository-level regression coverage proving `create_import()` returns a complete `ContactImportRecord` and uses full-row mappings. |
| `docs/evidence/phase-4-local-docker-e2e-fix-2-contact-import.md` | New evidence file for this slice. |
| Phase 4 tracking docs | Updated after verification. |

Repository behavior before:

```text
.returning(ContactImport).scalars().one()
.returning(Contact).scalars().one()
.returning(ContactImportRow).scalars().one()
```

Repository behavior after:

```text
.returning(*_CONTACT_IMPORT_COLUMNS).mappings().one()
.returning(*_CONTACT_COLUMNS).mappings().one()
.returning(*_CONTACT_IMPORT_ROW_COLUMNS).mappings().one()
```

Also converted contact import reads and contact read repository results to explicit columns + mappings so the read path remains consistent with the write fix.

Why tenant/RLS/idempotency behavior is preserved:

- The router still resolves `current_principal`.
- The router still builds `CsvImportService` inside `tenant_session(...)`.
- The repository still receives a tenant-scoped connection from `tenant_session`.
- Tenant predicates were preserved on contact reads, dedupe lookups, import status updates, and contact/import-row operations.
- Service-layer RBAC, billing, compliance suppression, idempotency, validation, and audit behavior were not bypassed.
- No direct DB calls were added to route handlers.

---

## 4. Repository scalar-mapping audit

Audit command summary:

```text
python -c "... scan backend/app/repositories for files containing both .returning(...) and .scalars() ..."
```

Risky same-pattern repository files still present after the campaign/idempotency/contact fixes:

| Repository | Status |
|---|---|
| `billing_repo.py` | Deferred — not part of this local E2E path. |
| `compliance_repo.py` | Deferred — likely future same-pattern risk for write paths. |
| `draft_repo.py` | **Current next blocker candidate.** Draft generation returned 500 after contact import and campaign selection passed; `draft_repo.py` still uses `returning(Draft).scalars()` and `returning(DraftEvidence).scalars()`. |
| `followup_repo.py` | Deferred. |
| `knowledge_repo.py` | Deferred. |
| `outcomes_repo.py` | Deferred. |
| `research_repo.py` | Deferred. |
| `review_repo.py` | Deferred. |
| `safety_repo.py` | Deferred. |
| `sending_repo.py` | Deferred. |
| `support_access_repo.py` | Deferred. |
| `tenant_repo.py` | Deferred. |

Fixed in this slice:

- `contact_repo.py` import/create/update/import-row/contact-read paths.

Previously fixed:

- `campaign_repo.py`.
- `idempotency_repo.py`.

Deferred follow-up:

```text
P4-LocalDockerE2E-Fix-3-DraftGeneration
```

Rationale for deferring broader repository changes:

- The instruction allowed fixing additional same-pattern bugs only when clearly identical, low-risk, and covered by tests.
- Contact import paths were directly in scope and covered by an added regression test plus existing CSV import tests.
- Draft generation is the next E2E blocker but should be handled in its own slice with draft/evidence-specific tests.

---

## 5. Tests added / updated

Added backend regression test:

| Test | Purpose |
|---|---|
| `test_contact_import_repository_create_returns_complete_import_record` | Verifies `ContactImportRepository.create_import()` returns a complete `ContactImportRecord`, preserves returned id/tenant/idempotency/status/count fields, and uses result mappings instead of scalar-only mapping. |

Targeted test:

| Command | Result |
|---|---|
| `python -m pytest tests/test_csv_import.py -q` | PASS — 16 tests |

---

## 6. Backend gate results

Commands run from `backend/`:

| Gate | Result |
|---|---|
| `python -m ruff check app tests` | PASS |
| `python -m black --check app tests` | PASS after formatting `contact_repo.py` |
| `python -m mypy --ignore-missing-imports app` | PASS — 156 source files checked |
| `python -m pytest -q` | PASS — full backend suite completed; existing Starlette/httpx deprecation warning remains |

Backend verdict: **PASS**.

---

## 7. Frontend gate results

No frontend files changed, but frontend gates were rerun because Docker E2E depends on the route surfaces.

Commands run from `frontend/`:

| Gate | Result |
|---|---|
| `npm run lint` | PASS |
| `npx tsc --noEmit` | PASS — used because `npm run typecheck` command was blocked by the tool wrapper, but it is the same typecheck command from `package.json` |
| `npm run test` | PASS — 4 files / 141 tests |
| `npm run build` | PASS — Next 14.2.35 generated 27 static pages |

Expected test stderr remains for network fallback and jsdom navigation behavior. Tests still pass.

Frontend verdict: **PASS**.

---

## 8. Docker compose and health results

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

## 9. Contact import verification

Docker backend contact import verification:

| Check | Result |
|---|---|
| `POST /api/v1/imports/contacts` with local mock auth token, demo tenant header, idempotency key, and CSV JSON body | PASS — HTTP 201 |
| Response includes complete safe import summary | PASS — returned `id`, `status`, `total_rows`, `valid_rows`, `invalid_rows`, and `duplicate_rows`; no raw CSV/contact PII returned. |
| `GET /api/v1/contacts` after import | PASS — HTTP 200 |
| DB contact existence check | PASS — local DB contained imported contact IDs after import. |
| Invalid/no-auth request clean failure | PASS — no-auth request returned 401, not 500. Tool safety blocked the malformed-body authenticated check, so that specific invalid-body check was not completed. |

Observed safe import response:

```text
{
  "import": {
    "id": "62b1d1d2-47e1-400f-81b0-34aebddf1a80",
    "status": "completed",
    "total_rows": 1,
    "valid_rows": 1,
    "invalid_rows": 0,
    "duplicate_rows": 0
  },
  "idempotency_replay": false
}
```

Contact import verdict: **FIXED**.

---

## 10. Frontend Docker route smoke

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

## 11. Resumed happy-path E2E result

Result: **PARTIAL / STILL BLOCKED AFTER CONTACT IMPORT**.

| Flow | Result | Notes |
|---|---|---|
| Login page loads | PASS | `/login` route smoke 200. |
| Demo login works | PARTIAL | Local mock auth API was already verified in prior Docker retry; full browser click-through was not completed by shell tool. |
| Dashboard loads | PASS | `/dashboard` 200. |
| Contact import works | **PASS** | Docker backend `POST /api/v1/imports/contacts` now returns 201. |
| Contacts/prospects list updates | **PASS** | `GET /api/v1/contacts` returns 200 and DB contains imported contact IDs. |
| Campaign create works | PASS | Fixed in previous slice; campaign list remained available. |
| Campaign contact selection works | **PASS** | Docker backend campaign-contact selection returned 201 using an imported contact ID and existing campaign ID. |
| Draft/evidence/review queue happy path | **BLOCKED** | Draft generation request reached backend and returned 500. |
| Human approval path visible | PARTIAL | Route loads; valid draft chain not reached. |
| Send-gate dry run happy path | BLOCKED | Needs valid draft. |
| Mock send intent happy path | BLOCKED | Needs valid approved draft. |
| Outbound/audit trail | PARTIAL | Routes load; full action chain not completed. |
| Billing/access UI | PASS | `/billing` 200. |
| Compliance/suppression UI | PASS | routes 200. |
| No real provider action occurs | PASS | No provider/staging/production work occurred. |

New blocker after contact import fix:

```text
POST /api/v1/drafts/generate -> 500
```

The exact backend stack trace could not be captured because the tool wrapper blocked the backend log command after the draft request. However, repository audit shows `backend/app/repositories/draft_repo.py` still uses the same risky pattern on the next write path:

```text
.returning(Draft).scalars().one()
.returning(DraftEvidence).scalars().one()
.returning(Draft).scalars().first()
```

Interpretation:

- Contact import is fixed.
- Local E2E now advances to campaign-contact selection and then draft generation.
- The next likely source-fix slice is draft/evidence repository row mapping.

---

## 12. Safety confirmation

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
| Idempotency bypassed | NO |
| Frontend-only gate trust introduced | NO |
| `p4/next15-upgrade` merged | NO |

---

## 13. Remaining blockers

| Blocker | Status | Required next action |
|---|---|---|
| Draft generation write path | BLOCKED | Open a separate source-fix slice for `backend/app/repositories/draft_repo.py` row mapping and draft/evidence tests. |
| Full draft/review/send happy path | BLOCKED | Depends on draft generation fix, then possible downstream repository write-path checks. |
| Manual browser click-through | CAVEATED | Re-run after draft generation and downstream write paths pass. |
| `npm audit` on `master` | BLOCKED | Clean fix exists on `p4/next15-upgrade`; merge only when William approves. |
| `p4/next15-upgrade` | WAITING OWNER APPROVAL | Not merged in this slice. |
| Staging | PAUSED BY WILLIAM | Do not resume until owner signal. |
| AWS/deployment/registry/provider setup | PAUSED BY WILLIAM | Do not configure or request values yet. |
| Production | WAITING FIRST REAL CLIENT | No production work yet. |

---

## 14. Recommendation

Recommendation:

1. Treat `P4-LocalDockerE2E-Fix-2-ContactImport` as complete for the contact-import blocker.
2. Do not claim full local Docker happy-path E2E yet.
3. Open the next source-fix slice:

```text
P4-LocalDockerE2E-Fix-3-DraftGeneration
```

Suggested scope:

- inspect `backend/app/repositories/draft_repo.py`;
- fix `DraftRepository` and `DraftEvidence` row mappers to use explicit columns + `Result.mappings()`;
- add regression tests like this slice did;
- rerun backend/frontend/Docker checks;
- retry draft generation, evidence read, review queue, approval, send-gate dry run, mock send intent, outbound/audit.

Boss demo status:

- Contact import and campaign-contact selection now pass locally through Docker.
- Boss demo remains allowed only with caveats until draft generation and downstream happy path pass.

---

## 15. Final verdict

- P4-LocalDockerE2E-Fix-2-ContactImport: **PARTIAL COMPLETE**.
- Contact import: **FIXED**.
- Contact list/read after import: **PASS**.
- Campaign contact selection: **PASS**.
- Local Docker happy-path E2E: **STILL BLOCKED** by draft generation 500.
- Boss demo: **allowed only with caveats**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
