# Managed Clerk AuthService Wiring (P3-3c)

**Purpose:** Evidence that the backend managed-auth path is wired to use `ClerkJwksVerifier` through the existing `AuthService`/`current_principal` chain, that the local/mock path remains isolated to non-production only, and that the MFA enforcement primitive is wired (and confirmed no-op until `platform_admin` is added to the RBAC matrix).
**Source sections:** Master guide §3 (auth boundary), §9 (session lifecycle), §10 (credential encryption), §25 (launch blockers)
**Status:** Draft
**Related docs:** [phase-3-3b-clerk-verifier-implementation.md](phase-3-3b-clerk-verifier-implementation.md) · [phase-3-3a-clerk-auth-readiness-plan.md](phase-3-3a-clerk-auth-readiness-plan.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [AUTH_AND_RBAC](../AUTH_AND_RBAC.md)

---

## 1. Verdict

**P3-3c (managed Clerk AuthService wiring): COMPLETE — 2026-06-26**

Production auth path is **wired but not enabled**. Real Clerk issuer/secrets are not configured; no production cutover. The managed path constructs the right object graph when a valid issuer is configured; the local/mock path is unchanged and isolated.

- Managed `ClerkJwksVerifier` singleton wired at startup: **ready** (`app.state.clerk_verifier` set when issuer is configured and non-placeholder)
- Per-request DB-backed `AuthService` via `auth_context_session()`: **wired**
- Local/mock isolation: **unchanged** (`app.state.auth_service` only set when `not is_production AND mock_verifier`)
- MFA `enforce_mfa()` call in `current_principal`: **wired, confirmed no-op** for all 7 current RBAC roles
- Production not enabled: **confirmed** — no real Clerk secrets; no issuer configured in any committed env
- Frontend Clerk widget: **not wired** (deferred to P3-3d or post-owner-approval)

---

## 2. Owner decisions recorded

All 6 Clerk owner decisions gating P3-3b/P3-3c are now resolved (see `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` §2):

| # | Decision | Answer |
|---|----------|--------|
| 1 | Clerk project/environment | Separate Clerk Production project + separate dev/staging instances |
| 2 | Production domain + allowed origins | `https://app.automatedstructure.com` — no localhost/preview/wildcards |
| 3 | Tenant/user bootstrap process | Manual bootstrap for first pilot; no public signup |
| 4 | Platform-admin MFA mandatory at launch? | Yes — mandatory (enforcement wired; activates when role is added) |
| 5 | First client onboarding method | Manual bootstrap; Clerk invite flow later |
| 6 | Clerk dashboard ownership | Platform Engineering / DevOps owns keys/domains; Security/CTO approves MFA/JWT templates; SaaS owner approves onboarding/role model |

---

## 3. Files changed

| File | Change |
|------|--------|
| `backend/app/auth/managed.py` | New — `is_managed_auth_configured(settings)`, `make_managed_auth_service(verifier, conn)` |
| `backend/app/main.py` | Added managed-auth wiring branch: sets `app.state.clerk_verifier` when issuer configured |
| `backend/app/auth/dependencies.py` | Converted `auth_service` to async generator dep; mock path preserved; MFA wired in `current_principal` |
| `backend/tests/test_auth.py` | Added 4 tests; updated 1 |

---

## 4. Managed AuthService wiring

### 4.1 Startup wiring (`main.py`)

```
if not is_production and mock_verifier:
    app.state.auth_service = build_local_mock_auth_service()   ← mock path (unchanged)
elif auth_provider == "managed" and is_managed_auth_configured(settings):
    app.state.clerk_verifier = build_managed_clerk_verifier(settings)  ← new managed path
# else: neither → AUTH_NOT_CONFIGURED on each request (fail-closed)
```

`is_managed_auth_configured()` checks: issuer non-None, len ≥ 8, and none of `("change_me", "changeme", "placeholder", "todo", "xxx")` — same markers as `boot_guard._is_placeholder`. The check prevents `CHANGE_ME_PLACEHOLDER` or `None` from wiring a verifier with a garbage issuer.

`ClerkJwksVerifier` is a **singleton** — `HttpxJwksSource` holds the JWKS TTL cache; a singleton ensures the cache persists across requests.

### 4.2 Per-request dependency (`auth_service` dep)

```
auth_service() generator:
  1. check app.state.auth_service  → if set (mock path), yield it, done
  2. check app.state.clerk_verifier → if None, raise 500 AUTH_NOT_CONFIGURED (fail-closed)
  3. async with auth_context_session() as conn:
       yield make_managed_auth_service(verifier, conn)
```

`UserRepository`, `MembershipRepository`, `AuthSessionRepository` are created per-request with a fresh `AsyncConnection` from `auth_context_session()`. The session sets `app.auth_context='on'` transaction-locally — the correct pre-tenant context for auth queries (no `app.current_tenant_id` needed at this stage; tenant resolution is explicit via `X-Tenant-ID`).

### 4.3 Downstream chain — unchanged

`current_principal` → `AuthService.resolve_principal(token, tenant_id)` → verify → session revocation → user lookup → membership → `CurrentPrincipal`. Error codes unchanged: `UNAUTHENTICATED` 401, `AUTH_SESSION_REVOKED` 401, `TENANT_ACCESS_DENIED` 403.

---

## 5. Local/mock isolation

| Condition | Path | Auth service |
|-----------|------|-------------|
| `is_production=False, mock_verifier=True` (local dev default) | Mock | `app.state.auth_service` = `LocalMockClerkVerifier`-backed singleton |
| `is_production=False, mock_verifier=False, issuer set` | Managed | Per-request with `ClerkJwksVerifier` + DB repos |
| `is_production=True, mock_verifier=True` | BOOT FAIL | Boot guard raises `BootGuardError` before any request |
| `is_production=True, mock_verifier=False, issuer valid` | Managed | Per-request with `ClerkJwksVerifier` + DB repos |
| `is_production=True, issuer unset/placeholder` | BOOT FAIL | Boot guard raises `BootGuardError` |

`LocalMockClerkVerifier` **cannot reach production** — the boot guard rejects `mock_verifier=True` in production unconditionally ("`controlled_demo does not bypass auth`").

---

## 6. MFA enforcement

`enforce_mfa(principal, required_roles=mfa_required_roles(settings))` called in `current_principal` after principal is resolved.

**Current status: no-op for all live traffic.** `AUTH_MFA_REQUIRED_ROLES` defaults to `"platform_admin"`. The RBAC matrix (`services/authz.py`) has 7 roles: owner/admin/marketer/reviewer/viewer/billing_admin/support — none match. `enforce_mfa` returns immediately for every real principal.

When `platform_admin` is added to the RBAC matrix, enforcement activates automatically — no code change needed in `dependencies.py`.

**Blocker:** `platform_admin` must be added to RBAC matrix + DB `user_memberships` role column check constraint + migration before MFA enforcement becomes active. Recorded in `LAUNCH_BLOCKERS §7`.

---

## 7. Tests

Backend gates: **570 passed, 0 failed** (was 525 before P3-3b+P3-3c). New tests:

| Test | Asserts |
|------|---------|
| `test_production_wires_clerk_verifier_not_mock` | `create_app()` with `APP_ENV=production` + valid `AUTH_PROVIDER_ISSUER` → `app.state.clerk_verifier` is `ClerkJwksVerifier`; `app.state.auth_service` is `None` |
| `test_managed_auth_service_uses_correct_store_types` | `make_managed_auth_service(verifier, MagicMock())` → `AuthService` with correct `_verifier`, `_users` (`UserRepository`), `_memberships` (`MembershipRepository`), `_sessions` (`AuthSessionRepository`) |
| `test_current_principal_enforces_mfa_for_platform_admin_role` | `enforce_mfa()` raises `AppError(code="MFA_REQUIRED", status_code=403)` for `platform_admin` role with `mfa_verified=False` |
| `test_current_principal_mfa_noop_for_existing_roles` | All 7 current RBAC roles pass `enforce_mfa()` without raising (role not in required set) |
| `test_production_app_does_not_attach_mock_verifier` (updated) | Added: also asserts `app.state.clerk_verifier is None` when issuer is unset (default) |

Frontend gates: **122 passed, 0 failed** — no frontend changes; confirmed no regressions.

---

## 8. Remaining blockers before production cutover

| Blocker | Status |
|---------|--------|
| Real Clerk project provisioned (Production + dev/staging instances) | Not done — owner action required |
| `AUTH_PROVIDER_ISSUER`, `AUTH_PROVIDER_SECRET_KEY`, `AUTH_PROVIDER_PUBLISHABLE_KEY` sourced from AWS Secrets Manager | Not done — requires real Clerk project |
| Frontend `@clerk/nextjs` `ClerkProvider` + `getToken()` wired | Not done — deferred (P3-3d scope) |
| Real-JWT end-to-end smoke with real Clerk (no mock JWKS) | Not done — requires real Clerk project |
| `platform_admin` role added to RBAC matrix + DB schema | Not done — owner decision on role model required (LAUNCH_BLOCKERS §7) |
| P3-5/P3-6 stop gates | Unchanged — gated |

---

## 9. Honest limits

- **Production not enabled.** No real Clerk issuer/secrets committed or used. Managed auth path wired but unconfigured.
- **No real Clerk secrets.** All new config fields are `None` or absent in committed code; `.env.example` placeholders only.
- **No frontend Clerk widget.** `frontend/lib/clerk.tsx` is unchanged — still mock/stub only.
- **No real-JWT smoke.** Verifier tested with local RSA key fixtures only (no real Clerk JWTs).
- **No providers/sending/Stripe/SMS/live scraping.** All deferred.
- **MFA enforcement inert.** `platform_admin` role does not exist; `enforce_mfa()` is a no-op for all live traffic.
- **`JWKS-unavailable → 503 AUTH_UNAVAILABLE`** mapping still deferred (currently falls through to 401 via `TokenVerificationError`; noted in P3-3b evidence).
