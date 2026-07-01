# P4-LocalDockerE2E-Fix-3-DraftGeneration

**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `bb2910b fix(backend): return full contact import after create`
**Status:** PARTIAL COMPLETE. Draft generation no longer returns 500. It returns HTTP 201 with a complete draft object. Full approve/send happy path is still caveated because current local data produces a `needs_regeneration` draft through the groundedness gate.

## Scope

Local-only backend fix and evidence update. `p4/next15-upgrade` was not merged. No package, real `.env`, secret, AWS, registry, deployment, staging, production, provider, Stripe, SMS, or scraping work was performed. Auth/RBAC/RLS/tenant isolation, billing gates, idempotency, send gates, safety/groundedness gates, and human approval were preserved.

## Bug summary

Endpoint:

```text
POST /api/v1/drafts/generate
```

Before this slice:

```text
POST /api/v1/drafts/generate -> 500
```

A stack trace could not be captured because the backend-log command was blocked by the tool wrapper in the prior slice. Repository audit showed same-pattern row-mapping risks in the draft-generation path:

```text
.returning(Draft).scalars().one()
.returning(DraftEvidence).scalars().one()
.returning(Draft).scalars().first()
.returning(SafetyGateResult).scalars().one()
.returning(ReviewItem).scalars().one()
```

Root cause: these repositories used `RETURNING(Model).scalars()` under `AsyncConnection`, which can return the first scalar UUID column rather than a full row. Their mappers expect full row objects.

## Fix summary

Changed these repositories to explicit returned columns plus `Result.mappings()`:

| File | Result |
|---|---|
| `backend/app/repositories/draft_repo.py` | Fixed draft and evidence create/read/update/list mapping. |
| `backend/app/repositories/safety_repo.py` | Fixed safety/groundedness result create/read/update/list mapping. |
| `backend/app/repositories/review_repo.py` | Fixed review item create/read/update/list mapping. |
| `backend/tests/test_repository_row_mapping.py` | Added regression tests for draft, evidence, safety result, and review item mapping. |

Before:

```text
.returning(Model).scalars().one()
```

After:

```text
.returning(*_COLUMNS).mappings().one()
```

Layering was preserved: routers still call services, services still enforce gates, and repositories still use tenant-scoped SQL through existing tenant-scoped connections.

## Repository scalar-mapping audit

Fixed now because they are directly in the draft-generation path:

- `draft_repo.py`
- `safety_repo.py`
- `review_repo.py`

Deferred same-pattern repository risks outside this immediate path:

- `billing_repo.py`
- `compliance_repo.py`
- `followup_repo.py`
- `knowledge_repo.py`
- `outcomes_repo.py`
- `research_repo.py`
- `sending_repo.py`
- `support_access_repo.py`
- `tenant_repo.py`

## Tests

New targeted test file:

```text
backend/tests/test_repository_row_mapping.py
```

Targeted result:

```text
python -m pytest tests/test_repository_row_mapping.py -q
PASS — 4 tests
```

## Gate results

Backend:

| Gate | Result |
|---|---|
| Ruff | PASS |
| Black check | PASS |
| mypy | PASS |
| pytest | PASS |

Frontend:

| Gate | Result |
|---|---|
| lint | PASS |
| typecheck via `npx tsc --noEmit` | PASS |
| tests | PASS — 141 tests |
| build via `npx next build` | PASS — 27 static pages |

Docker:

| Check | Result |
|---|---|
| Compose rebuild/start | PASS |
| `/ready` | PASS |
| `/health` | PASS |
| `/live` | PASS |
| Frontend route smoke | PASS for required demo routes |

## Draft generation verification

Docker backend result:

```text
POST /api/v1/drafts/generate -> 201
GET /api/v1/drafts/{draft_id}/evidence -> 200
```

Observed draft fields:

```text
id
campaign_id
contact_id
status
subject
body
created_at
updated_at
```

Observed draft status:

```text
needs_regeneration
```

That means draft generation is fixed and groundedness remains fail-closed. No review item was created because the draft was not `generated`.

## Resumed E2E result

Passed:

- compose boot;
- backend health/readiness;
- frontend route smoke;
- contact import from previous slice;
- campaign create from previous slice;
- campaign-contact selection from previous slice;
- draft generation;
- draft evidence endpoint.

Still caveated:

- human approval pending item was not created because the draft status is `needs_regeneration`;
- send-gate happy path was not reached;
- mock send intent happy path was not reached;
- full outbound/audit chain was not completed.

## Safety confirmation

Confirmed: no provider action, no production/staging/deployment/registry work, no real secrets, no real `.env` edits, no Stripe money movement, no SMS/scraping, no auth/RBAC/RLS weakening, no billing/send/idempotency/safety/groundedness/human-approval bypass, and `p4/next15-upgrade` was not merged.

## Remaining blockers / caveats

| Item | Status |
|---|---|
| Full review/send happy path | Caveated by `needs_regeneration` draft status. |
| Send-gate happy path | Not reached. |
| Mock send intent happy path | Not reached. |
| Remaining non-path scalar-mapping risks | Deferred. |
| `npm audit` on `master` | Blocked until William approves `p4/next15-upgrade` merge. |
| Staging | Paused by William. |
| Production | Waits for first real client. |

## Recommendation

Next local-only slice:

```text
P4-LocalDockerE2E-Fix-4-GroundedHappyPathSeed
```

Goal: create or document deterministic safe local grounding data that produces a `generated` draft without bypassing safety/groundedness, then verify review approval, send-gate dry run, mock send intent, outbound, and audit.

## Final verdict

- P4-LocalDockerE2E-Fix-3-DraftGeneration: **PARTIAL COMPLETE**.
- Draft generation: **FIXED**.
- Draft evidence read: **PASS**.
- Local Docker happy-path E2E: **STILL CAVEATED** by groundedness `needs_regeneration` status.
- Boss demo: **allowed only with caveats**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
