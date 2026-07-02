# P4-FinalManualDemoSmoke

**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `44ac8d7 fix(backend): harden repository row mappings`
**Status:** BLOCKED for final sign-off. The core local/mock demo chain passed end to end, but the required logout -> login cycle failed after backend logout revoked the shared local mock session reference.

## Scope

Evidence-only final local demo smoke. No backend, frontend, migration, package, Dockerfile, workflow, `.env`, deployment, provider, staging, billing-money, SMS, or live-scraping change was made.

This smoke follows the approved no-browser-automation method: frontend route render checks are verified through the live Next.js container with HTTP 200 responses, and the backend API calls a real click would trigger are driven with the local mock auth header:

```text
Authorization: Bearer token-sentinel
X-Tenant-ID: 22222222-2222-2222-2222-222222222222
```

This does not imply a physical browser click-through. It confirms the same live frontend routes and backend JSON responses the local mock UI depends on.

## Preflight and Docker status

| Check | Result | Evidence |
|---|---|---|
| Current branch | PASS | `master` |
| Starting commit | PASS | `44ac8d7` |
| Starting working tree | PASS | clean |
| `p4/next15-upgrade` | PASS | branch exists and remains unmerged |
| Docker services | PASS | backend, frontend, db, n8n, and worker were running; db healthy |
| `GET /health` | PASS | HTTP 200, `{"status":"ok"}` |
| `GET /live` | PASS | HTTP 200, `{"status":"alive","service":"backend"}` |
| `GET /ready` | PASS | HTTP 200, `database: ok`, `migrations: up_to_date`, `rate_limit_backend: in_memory` |
| Frontend `/login` | PASS | HTTP 200 |
| Frontend `/dashboard` | PASS | HTTP 200 |

## Fresh smoke run

Run ID: `20260702094448`

Created during this smoke:

| Object | ID |
|---|---|
| Contact | `7a252ec9-f6d9-4918-88b0-a0e166cf404e` |
| Campaign | `f7090186-7d08-4606-b4b9-6e408f6961c4` |
| Campaign contact selection | `715db254-0a70-41b7-8ccd-e4094303d14b` |
| Draft | `326f2467-c956-49b1-8837-4e23f426d5b5` |
| Review item | `c6818433-55c4-4c36-b10b-786d5518b41a` |
| Outbound message | `38b78193-aacd-46b5-b7d5-6ca31850e2f4` |

| # | Step | Result | Observed response | Detail |
|---:|---|---|---|---|
| 1 | Login page renders | PASS | HTTP 200 | `/login` |
| 2 | Demo mock session exchange | PASS | HTTP 200 | Tenant resolved as `22222222-2222-2222-2222-222222222222` |
| 3 | Dashboard page renders after demo login | PASS | HTTP 200 | `/dashboard` |
| 4 | Prospects page renders | PASS | HTTP 200 | `/prospects` |
| 5 | Import a contact | PASS | HTTP 201 | `status=completed`, `valid_rows=1` |
| 6 | Verify contact list | PASS | HTTP 200 | Imported contact found by generated local-demo email |
| 7 | Campaigns page renders | PASS | HTTP 200 | `/campaigns` |
| 8 | Create campaign | PASS | HTTP 201 | New campaign ID above |
| 9 | Campaign detail page renders | PASS | HTTP 200 | `/campaigns/f7090186-7d08-4606-b4b9-6e408f6961c4` |
| 10 | Select campaign contact | PASS | HTTP 201 | New campaign-contact selection ID above |
| 11 | Seed local grounding data | PASS | Docker exec exit 0 | `SKIPPED (already_seeded)` for seeded local demo document `b95785a6-1f0c-471c-8414-d5c49be3439b` |
| 12 | Generate grounded draft | PASS | HTTP 201 | Draft created with `status=generated` |
| 13 | Read draft evidence | PASS | HTTP 200 | 2 evidence rows, source type `knowledge_chunk` |
| 14 | Review queue page renders | PASS | HTTP 200 | `/review-queue` |
| 15 | Review queue API returns item | PASS | HTTP 200 | Review item found for generated draft |
| 16 | Human approval | PASS | HTTP 200 | Review status `approved` |
| 17 | Send-gate dry run | PASS | HTTP 200 | `status=passed`, `mock_only=True` |
| 18 | Mock send intent | PASS | HTTP 201 | `mock_only=True`; outbound message ID above |
| 19 | Outbound message record | PASS | HTTP 200 | Outbound status `mock_sent` |
| 20 | Audit trail | PASS | HTTP 200 | Chain present: `draft.generated`, `draft.approved`, `send_gate.passed`, `outbound_message.sent` |
| 21 | Billing page renders | PASS | HTTP 200 | `/billing` |
| 22 | Billing subscription API | PASS | HTTP 200 | `tenant_status=active`, `mock_only=True` |
| 23 | Billing access API | PASS | HTTP 200 | `mock_only=True`; response keys `access,mock_only` |
| 24 | Compliance settings page renders | PASS | HTTP 200 | `/settings/compliance` |
| 25 | Compliance profile API | PASS | HTTP 200 | `mock_only=True`; response keys `compliance_profile,mock_only` |
| 26 | Suppression settings page renders | PASS | HTTP 200 | `/settings/suppression` |
| 27 | Suppressions API | PASS | HTTP 200 | `suppressions=0`, `mock_only=True` |
| 28 | Deliverability page renders | PASS | HTTP 200 | `/deliverability` |
| 29 | Deliverability API | PASS | HTTP 200 | `mock_only=True`; response keys `deliverability,mock_only` |
| 30 | Mailbox health API | PASS | HTTP 200 | `mock_only=True`; response keys `mailbox_health,mock_only` |
| 31 | Outcomes page renders | PASS | HTTP 200 | `/outcomes` |
| 32 | Outcomes API | PASS | HTTP 200 | `mock_only=True`; response keys `mock_only,outcomes` |
| 33 | Login page still renders before logout cycle | PASS | HTTP 200 | `/login` |
| 34 | Dashboard still renders before logout cycle | PASS | HTTP 200 | `/dashboard` |
| 35 | Backend logout | PASS | HTTP 200 | `revoked=1` |
| 36 | Login page renders after logout | PASS | HTTP 200 | `/login` |
| 37 | Backend-side demo session after logout | FAIL | HTTP 401 | `AUTH_SESSION_REVOKED` |
| 38 | Alternate local mock token after logout | FAIL | HTTP 401 | `AUTH_SESSION_REVOKED` |

## Blocker found

The final logout -> login cycle is blocked in the backend-side mock flow approved for this evidence method.

Observed behavior:

```text
POST /auth/logout -> 200, {"revoked": 1}
POST /auth/session with token-sentinel -> 401 AUTH_SESSION_REVOKED
POST /auth/session with fake-valid-token -> 401 AUTH_SESSION_REVOKED
```

Cause from code inspection:

- `backend/app/auth/local_mock.py` maps both local mock tokens (`token-sentinel`, `fake-valid-token`) to the same fixed provider session reference: `local_mock_session_ref`.
- `backend/app/auth/local_mock.py::_LocalMockSessions.revoke()` stores that provider session reference in an in-memory revoked set.
- `backend/app/services/auth.py::resolve_principal()` checks `is_revoked()` before resolving the principal and correctly returns `AUTH_SESSION_REVOKED` once the fixed local mock session reference has been revoked.

This is not a production-auth finding. It is a local/mock demo-session lifecycle defect that makes the same backend process unable to sign in again after logout unless the backend is restarted or the local mock session-cycle logic is fixed.

Recommended follow-up fix slice: **P4-LocalMockAuthSessionCycle-Fix**.

Expected scope for that follow-up: repair the local/mock demo logout -> login cycle without weakening managed Clerk auth, app-side revocation, tenant membership checks, MFA checks, RBAC, RLS, or production boot guard. A likely safe direction is to make the local mock sign-in session reference per-session instead of a single process-global fixed reference, or to separate frontend demo sign-out state from backend provider-session revocation in local mock mode. This slice did not implement that fix.

## Rough edges and non-blockers

| Item | Classification | Notes |
|---|---|---|
| Long shell helper ended with a trailing quote after the audit PASS lines | Evidence-capture artifact | The printed observations through audit had already completed. Remaining billing/compliance/dashboard/logout checks were run in a separate transparent batch. |
| `/api/v1/outcomes/roi` without `campaign_id` | Not part of this final page smoke | The route requires `campaign_id`; `/outcomes` page and `GET /api/v1/outcomes` both passed. Recheck `/api/v1/outcomes/roi?campaign_id=<id>` after the auth-cycle fix if it is added to the boss demo script. |

## Safety confirmation

- No live email was sent.
- The send-gate was exercised and returned `passed`; it was not bypassed.
- The send intent was mock-only and returned `mock_only=True`.
- The outbound message record was `mock_sent`.
- Billing APIs returned `mock_only=True`; no Stripe checkout, portal, webhook, billing-state mutation, or money movement was exercised.
- Compliance profile and suppression APIs were read-only in this smoke.
- No Resend send, SMS, live scraping, AWS provisioning, registry push, staging deploy, or production cutover occurred.
- No package, source, migration, Dockerfile, workflow, or `.env` file was changed.
- `p4/next15-upgrade` remained unmerged.

## Final verdict

Core local/mock boss-demo surface: **PASS with one caveat**.

Final manual demo smoke sign-off: **BLOCKED** until **P4-LocalMockAuthSessionCycle-Fix** or an explicit demo-script decision removes the backend logout -> re-login step.

Staging remains paused by William. Production remains blocked until the first real client and separate owner/operator approvals. Real providers remain disabled.
