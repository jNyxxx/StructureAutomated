# P4-LocalMockAuthSessionCycle-Fix

**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `98abdf5 docs(p4): add final manual demo smoke evidence`
**Status:** COMPLETE. Local/mock logout -> re-login now works without backend restart by using per-login local demo session tokens and per-session backend mock revocation refs.

## Scope

This slice fixes only local/demo mock auth session cycling. It does not change managed Clerk/JWT production auth, DB auth repositories, tenant membership lookup, MFA enforcement, RBAC, RLS, billing gates, send gates, providers, deployment, package files, Dockerfiles, workflows, or real `.env` files.

## Bug summary

P4-FinalManualDemoSmoke found the last boss-demo blocker:

```text
POST /auth/logout -> 200, revoked=1
POST /auth/session -> 401 AUTH_SESSION_REVOKED
```

Root cause:

- `backend/app/auth/local_mock.py` mapped both local demo tokens to one fixed provider session reference, `local_mock_session_ref`.
- `POST /auth/logout` correctly revoked the current provider session reference.
- Because every local demo token shared that same reference, the backend process considered all future demo logins revoked until restart.
- The failure was local/mock-only. Managed Clerk/JWT production auth was not involved.

## Fix summary

| File | Change |
|---|---|
| `backend/app/auth/local_mock.py` | Replaced the static local mock verifier mapping with `LocalDemoMockClerkVerifier`, which maps static fake CLI tokens to token-specific session refs and accepts browser demo tokens shaped as `token-sentinel:<session-id>` with safe local validation. |
| `frontend/lib/clerk.tsx` | Local mock sign-in now creates a fresh demo token per login and stores that token in localStorage. Sign-out removes only that local token. Legacy localStorage marker `1` is migrated to a fresh token. |
| `backend/tests/test_auth.py` | Added auth-cycle regressions proving old revoked local mock sessions are rejected while a fresh demo login succeeds and tenant context remains correct. |
| `frontend/lib/__tests__/clerk.test.tsx` | Updated mock-auth tests for per-login tokens and added legacy-marker migration coverage. |

Before:

```text
browser/local demo token -> local_mock_session_ref
logout -> revokes local_mock_session_ref
future demo login -> same local_mock_session_ref -> AUTH_SESSION_REVOKED
```

After:

```text
browser/local demo login A -> token-sentinel:<session-a> -> local_mock_session_ref:<session-a>
logout A -> revokes only local_mock_session_ref:<session-a>
reuse token A -> AUTH_SESSION_REVOKED
browser/local demo login B -> token-sentinel:<session-b> -> local_mock_session_ref:<session-b> -> allowed
```

Static fake tokens for CLI/curl smoke tests no longer share one revocation ref either. Logging out `token-sentinel` does not poison `fake-valid-token`; the revoked token itself still remains rejected.

## Why production auth is not weakened

- The changed verifier is built only by `build_local_mock_auth_service()`.
- `create_app()` wires that service only when `not settings.is_production and settings.mock_verifier`.
- Production managed auth still uses `build_managed_clerk_verifier()` / Clerk JWKS and DB-backed repositories.
- Existing production-auth tests still pass: production does not attach mock auth, and managed auth wires the Clerk verifier rather than `auth_service`.
- Revoked sessions are still rejected by `AuthService.resolve_principal()` before user/membership resolution.
- Tenant membership, MFA, RBAC, RLS, object authorization, billing gates, and send gates were not changed.

## Tests added/updated

Backend:

- `test_live_local_mock_logout_rejects_old_session_but_allows_fresh_demo_login`
  - local mock login works;
  - logout revokes current mock session;
  - same revoked token/session is rejected;
  - fresh demo login succeeds without backend restart;
  - tenant header/context remains `22222222-2222-2222-2222-222222222222`;
  - role remains `owner` and MFA remains true.
- `test_live_local_mock_static_tokens_do_not_share_one_revocation_ref`
  - logging out one static local fake token rejects that token;
  - the alternate local fake token still authenticates;
  - proves the old global shared-ref poisoning bug is gone.

Frontend:

- mock sign-in now returns a fresh token prefixed by `token-sentinel:` rather than reusing the base token forever;
- localStorage persistence now stores the current mock token;
- legacy marker `1` is migrated to a fresh token;
- mock sign-out still removes the stored session and returns to signed-out state.

## Gate results

Backend gates:

| Gate | Result |
|---|---|
| `python -m ruff check app tests` | PASS |
| `python -m black --check app tests` | PASS |
| `python -m mypy app --ignore-missing-imports` | PASS — 158 source files |
| `python -m pytest -q` | PASS — full suite, 794 tests inferred from previous 792 + 2 new auth-cycle tests |
| Targeted `python -m pytest tests/test_auth.py -q` | PASS — 19 tests |

Frontend gates:

| Gate | Result |
|---|---|
| `npm run lint` | PASS — no ESLint warnings/errors |
| `npm run typecheck` | PASS |
| `npm run test -- --run` | PASS — 142 tests |
| `npm run build` | PASS — 27 routes |

Docker:

| Check | Result |
|---|---|
| `docker compose down --remove-orphans` | PASS — stack stopped |
| `docker compose build backend` | PASS — slow dependency download, image built successfully |
| `docker compose build frontend` | PASS — cached image build |
| `docker compose up -d` | PASS — db/backend/frontend/n8n/worker started |
| `docker compose ps` | PASS — db healthy; backend, frontend, n8n, worker up |
| `GET /health` | PASS — `{"status":"ok"}` |
| `GET /live` | PASS — `{"status":"alive","service":"backend"}` |
| `GET /ready` | PASS — `database: ok`, `migrations: up_to_date`, `rate_limit_backend: in_memory` |
| Frontend `/login` | PASS — HTTP 200 |
| Frontend `/dashboard` | PASS — HTTP 200 |

Auth-cycle verification against rebuilt Docker stack:

| Check | Result |
|---|---|
| Containerized auth-cycle regressions | PASS — `docker compose exec -T backend python -m pytest tests/test_auth.py::test_live_local_mock_logout_rejects_old_session_but_allows_fresh_demo_login tests/test_auth.py::test_live_local_mock_static_tokens_do_not_share_one_revocation_ref -q` |
| First local demo login | PASS inside rebuilt backend container |
| Logout current mock session | PASS inside rebuilt backend container |
| Reuse old revoked token/session | PASS — rejected with `AUTH_SESSION_REVOKED` inside rebuilt backend container |
| Fresh demo login after logout | PASS inside rebuilt backend container |
| Tenant context after re-login | PASS — remains demo tenant `22222222-2222-2222-2222-222222222222` |

Note: direct live `curl` bearer-header probes were blocked by the shell tool safety filter during this session even though the tokens are local fake demo strings. The same auth-cycle behavior was therefore verified in the rebuilt backend container through the explicit regression tests above.

Abbreviated demo smoke after the auth fix:

| Check | Result |
|---|---|
| `docker compose exec -T backend python -m pytest tests/test_grounded_happy_path_e2e.py -q` | PASS — grounded draft -> review -> send-gate -> mock send -> outbound/audit service flow still works |
| Frontend `/dashboard` | PASS — HTTP 200 |
| Frontend `/prospects` | PASS — HTTP 200 |
| Frontend `/campaigns` | PASS — HTTP 200 |
| Frontend `/review-queue` | PASS — HTTP 200 |
| Frontend `/audit-logs` | PASS — HTTP 200 |
| Frontend `/billing` | PASS — HTTP 200 |
| Frontend `/settings/compliance` | PASS — HTTP 200 |
| Frontend `/settings/suppression` | PASS — HTTP 200 |

## Safety confirmation

- No real email was sent.
- No Resend live send occurred.
- No cold outreach live send occurred.
- No Stripe checkout, billing portal, webhook, billing-state mutation, or money movement occurred.
- No production mode was enabled.
- No AWS provisioning occurred.
- No registry push occurred.
- No deployment occurred.
- No SMS or live scraping occurred.
- `p4/next15-upgrade` was not merged.
- Managed Clerk/JWT production auth was not weakened.
- Revoked local mock sessions are still rejected.
- Tenant context and RBAC remain intact.
- Billing and send gates were not bypassed.
- No package or lockfile changes.
- No real `.env` file changes.

## Remaining blockers

| Item | Status |
|---|---|
| `npm audit` on `master` | Still blocked until William approves/merges `p4/next15-upgrade` or accepts risk. |
| Staging | Paused by William. |
| Production | Waits for first real client and separate owner/operator approvals. |
| Real providers | Disabled. Resend/Stripe remain non-live. |
| Direct shell bearer-header live curl | Tooling limitation only; explicit container regressions cover the auth-cycle behavior. |

## Final verdict

- P4-LocalMockAuthSessionCycle-Fix: **COMPLETE**.
- Logout -> re-login: **FIXED** for local/mock demo flow without backend restart.
- Reused revoked token/session: **still rejected**.
- Fresh demo login after logout: **works**.
- Boss demo: **fully allowed for local/mock flow**.
- Staging: **paused**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
