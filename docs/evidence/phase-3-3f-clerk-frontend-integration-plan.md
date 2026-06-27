# P3-3f — Frontend Clerk Integration & Real-JWT Smoke Plan

**Purpose:** Evidence for the P3-3f docs-only slice: frontend Clerk integration inspection,
integration design, env/config checklist, real-JWT smoke test plan, and remaining blockers.
**Status:** Complete (docs-only — no code changes).
**Related docs:** [AUTH_AND_RBAC](../AUTH_AND_RBAC.md) §5/§9 · [LAUNCH_BLOCKERS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) §6/§7 · [phase-3-3e-platform-admin-mfa-implementation.md](phase-3-3e-platform-admin-mfa-implementation.md)

---

## 1. Git state

- Branch: `master`
- HEAD at slice start: `844f6be` (P3-3e — platform_admin role + MFA enforcement)
- Docs-only slice — no code changes, no backend/frontend gate delta

---

## 2. Frontend auth inspection findings

### 2.1 @clerk/nextjs installed?
**NO.** Absent from both `dependencies` and `devDependencies` in `frontend/package.json`.

### 2.2 Current auth layer
`frontend/lib/clerk.tsx` contains a custom stub provider — **not** the real `@clerk/nextjs`.

| Symbol | Location | Role |
|---|---|---|
| `FrontendAuthState` | `clerk.tsx:9` | Interface: `{isLoaded, isSignedIn, userId, email, getToken, mode}` |
| `ClerkFrontendProvider` | `clerk.tsx:55` | Context provider; accepts `value?: FrontendAuthState` injection point |
| `useFrontendAuth()` | `clerk.tsx:69` | Hook; returns current `FrontendAuthState` |
| `AuthGate` | `clerk.tsx:88` | Route guard: blocks unauthenticated users; checks `mode === "local_mock"` in production |
| `ClerkAuthCard` | `clerk.tsx:125` | Login/signup UI; renders mock `<AuthCard>` |
| `isLocalMockAuthAllowed()` | `clerk.tsx:20` | Returns `NODE_ENV !== "production" OR NEXT_PUBLIC_CLERK_MOCK_MODE=true` |

Default state (no `value` prop): `{isSignedIn: false, getToken: async () => null, mode: "local_mock"}`.
In production without `NEXT_PUBLIC_CLERK_MOCK_MODE`: `AuthGate` and `ClerkAuthCard` both fail closed.

### 2.3 App router structure (auth-relevant)

```
frontend/app/
  layout.tsx                       ← root layout; mounts ClerkFrontendProvider
  (auth)/
    login/page.tsx                 ← renders <ClerkAuthCard mode="login">
    signup/page.tsx                ← renders <ClerkAuthCard mode="signup">
    forgot-password/page.tsx
    reset-password/page.tsx
    verify-email/page.tsx
  (app)/
    layout.tsx                     ← mounts AuthGate → TenantProvider → AppShell
    dashboard/page.tsx
    [... all protected pages ...]
```

No `middleware.ts` exists. Auth guard is client-side only (`AuthGate`).

### 2.4 API client auth
`frontend/lib/api-client.ts:131-143`:
- `authenticatedApiRequest()` requires caller-supplied `getToken: () => Promise<string|null>` and `getTenantId: () => string|null`.
- Injects `Authorization: Bearer ${token}` and `X-Tenant-ID: ${tenantId}` headers.
- **No changes needed** to `api-client.ts` — signature already matches Clerk's `getToken()`.

### 2.5 Tenant context
`frontend/lib/tenant-context.tsx` (`TenantProvider`):
- Calls `fetchAuthMe({getToken: auth.getToken, getTenantId: () => selectedTenantId})` after `auth.isSignedIn`.
- `selectedTenantId` starts as `null` when no `initialTenantId` prop is passed.
- If `selectedTenantId` is null → backend returns `400 TENANT_REQUIRED` → `TenantProvider.status = "session_unavailable"`.
- **Gap:** no tenant-selector page or "list my tenants" endpoint exists to bootstrap `selectedTenantId` after real login.

### 2.6 Backend auth chain (already complete)
| Component | Status |
|---|---|
| `ClerkJwksVerifier` (RS256/JWKS, fail-closed) | Done — P3-3b |
| `build_managed_clerk_verifier(settings)` | Done — P3-3b |
| `make_managed_auth_service(verifier, conn)` | Done — P3-3c |
| `auth_service()` dependency (mock vs managed dispatch) | Done — P3-3c |
| `current_principal()` dependency | Done — P3-3c |
| `enforce_mfa()` wired + active for `platform_admin` | Done — P3-3e |

All required backend env vars documented in `.env.example` as CHANGE_ME_PLACEHOLDER.

---

## 3. Integration design (implementation slice — requires Clerk values + owner approval)

### 3.1 New file: `frontend/lib/clerk-real.tsx`

Adapter that wraps `@clerk/nextjs` and maps its state to the existing `FrontendAuthState` interface:

```
RealClerkProvider (wraps ClerkProvider from @clerk/nextjs)
  └── RealClerkBridge (client component using useAuth() + useUser())
        └── ClerkFrontendProvider value={mappedFrontendAuthState}
              └── {children}
```

Mapping:
- `isLoaded` ← `isLoaded` (from `useAuth()`)
- `isSignedIn` ← `isSignedIn ?? false`
- `userId` ← `userId ?? null`
- `email` ← `user?.primaryEmailAddress?.emailAddress ?? null` (from `useUser()`)
- `getToken` ← `() => getToken()` (Clerk's `getToken`, identical signature)
- `mode` ← `"real_clerk"`

When `value` is supplied to `ClerkFrontendProvider`, the mock logic inside it is bypassed entirely.

### 3.2 Modified: `frontend/app/layout.tsx`

Conditional mount based on `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`:
- Present → mount `<RealClerkProvider>` (which wraps `ClerkFrontendProvider` internally)
- Absent → keep `<ClerkFrontendProvider>` as today (mock mode, no change)

Local demo mode is fully preserved: no publishable key → mock runs exactly as before.

### 3.3 Sign-in/sign-up pages

**A. Existing pages** (`(auth)/login`, `(auth)/signup`):
- Conditional: if key present → render Clerk's `<SignIn>` / `<SignUp>` component; else keep `<AuthCard>` mock.

**B. Catch-all routes** (required for Clerk OAuth/SSO callback routing):
- New: `frontend/app/(auth)/sign-in/[[...sign-in]]/page.tsx` → `<SignIn />`
- New: `frontend/app/(auth)/sign-up/[[...sign-up]]/page.tsx` → `<SignUp />`
- Clerk dashboard configuration: Sign-in URL = `/sign-in`, After sign-in = `/dashboard`.

### 3.4 No changes needed
- `frontend/lib/api-client.ts` — `getToken` signature already matches
- `frontend/lib/tenant-context.tsx` — already passes `auth.getToken` downstream
- `frontend/lib/clerk.tsx` — adapter already accepts `value` injection; no modification needed
- Backend auth chain — complete

### 3.5 Deferred
- `middleware.ts` (Next.js server-side route protection via Clerk middleware) — `AuthGate` client guard is sufficient for MVP; middleware is a hardening step
- Tenant selector page / `GET /auth/tenants` endpoint — required for multi-tenant users; deferred (see §5)
- `backend/app/auth/dependencies.py:73-74` stale comment cleanup — deferred to next code slice

---

## 4. Env/config checklist

### Frontend (`.env.local` — never committed, not in `.env.example`)
| Var | Value | Note |
|---|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_test_...` | From Clerk dev dashboard |
| `NEXT_PUBLIC_CLERK_MOCK_MODE` | unset or `false` | Remove for real-JWT smoke |

### Backend (`.env` — never committed; `.env.example` already has placeholders)
| Var | Example value | Note |
|---|---|---|
| `AUTH_PROVIDER_ISSUER` | `https://<instance>.clerk.accounts.dev` | Required |
| `AUTH_PROVIDER_PUBLISHABLE_KEY` | `pk_test_...` | Shape-checked only |
| `AUTH_PROVIDER_SECRET_KEY` | `sk_test_...` | Shape-checked only; never read into JWT claims |
| `AUTH_PROVIDER_AUTHORIZED_PARTIES` | `http://localhost:3000` | Prevents `azp` mismatch in local smoke |
| `AUTH_PROVIDER_AUDIENCE` | (empty) | Only if Clerk JWT template sets `aud` |
| `AUTH_PROVIDER_MFA_CLAIM` | `mfa_verified` | Required for MFA smoke; Clerk JWT template must emit this |
| `MOCK_VERIFIER` | `false` | Switches to managed Clerk path |

---

## 5. Tenant-selector gap

After real Clerk login, `selectedTenantId` starts null. `TenantProvider` calls `/auth/me`
with no `X-Tenant-ID` → backend returns `400 TENANT_REQUIRED`. The user is stuck.

**MVP smoke workaround (no new code):** pass `?tenant=<uuid>` query param; read it in the
`(app)/layout.tsx` and pass as `initialTenantId` to `TenantProvider`.

**Full solution (deferred):** add `GET /auth/tenants` endpoint returning the caller's active
memberships (tenant_id, role, tenant_name). After sign-in, redirect to a tenant-select page.
If user has exactly one membership, auto-select.

**Owner decision required:** auto-select first membership vs explicit selector page (recorded
in `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md §7`).

---

## 6. Real-JWT smoke checklist

**Prerequisites (all owner-gated — none available today):**
- [ ] Clerk dev project provisioned (free tier OK)
- [ ] One test user created in Clerk dev project
- [ ] Backend `.env` updated locally (NOT committed) with real values (§4)
- [ ] Frontend `.env.local` updated locally (NOT committed) with `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- [ ] Test tenant + user + membership seeded in DB (`provider_user_id` = Clerk `sub` claim from JWT)
- [ ] P3-3f code implementation complete (§3 above)

**Smoke steps:**
```
1.  docker-compose up db
2.  cd backend && alembic upgrade head   # applies 00022_platform_admin_role
3.  Seed DB:
      INSERT INTO tenants (...) VALUES (...);
      INSERT INTO users (provider_user_id='user_<clerk_id>', ...) VALUES (...);
      INSERT INTO tenant_memberships (tenant_id, user_id, role='owner') VALUES (...);
4.  APP_ENV=local MOCK_VERIFIER=false uvicorn app.main:app --reload
5.  cd frontend && npm run dev
6.  Open http://localhost:3000/?tenant=<tenant_uuid>
7.  Redirected to /sign-in → sign in with test Clerk user
8.  Browser: auth.isSignedIn=true, getToken() returns JWT (verify in DevTools → Application → Cookies)
9.  App calls GET /auth/me
      Authorization: Bearer <real_jwt>
      X-Tenant-ID: <tenant_uuid>
10. Backend:
      ClerkJwksVerifier fetches JWKS from https://<issuer>/.well-known/jwks.json
      Validates RS256 sig, iss, exp, azp
      resolve_principal() looks up user by provider_user_id
11. Response: HTTP 200 {"principal": {tenant_id, role: "owner", mfa_verified: false, ...}}
12. Frontend: TenantProvider.status = "ready", tenant confirmed
13. Navigate to /dashboard → data loads (billing mock gates active)
14. Sign out → AuthGate redirects to /sign-in
15. Error paths:
      Expired JWT       → expect 401 UNAUTHENTICATED
      Wrong issuer      → expect 401 UNAUTHENTICATED
      No membership row → expect 403 FORBIDDEN / TENANT_ACCESS_DENIED
16. Safety grep: no raw JWT in backend stdout/logs
```

---

## 7. Remaining blockers

| Blocker | Type | Status |
|---|---|---|
| Clerk dev project not provisioned | Owner action | Not done — owner must create |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Owner action | Not available |
| `AUTH_PROVIDER_ISSUER` | Owner action | Placeholder only |
| `AUTH_PROVIDER_SECRET_KEY` | Owner action | Placeholder only |
| Test user in Clerk dev project | Owner action | Not done |
| Test user + membership seeded in DB | Code/seed | Not done (needs Clerk user ID first) |
| Tenant-selector page / `GET /auth/tenants` | Owner decision + code | Deferred (§5) |
| `@clerk/nextjs` not installed | Code (no Clerk values needed) | Safe to install anytime |
| `dependencies.py:73-74` stale comment | Trivial cleanup | Deferred to next code slice |
| `middleware.ts` server-side guard | Code, hardening | Deferred post-smoke |
| `auth_provider_mfa_claim` in Clerk JWT template | Config, production cutover | Deferred |

---

## 8. Final verdict

**P3-3f = docs-only.** Real Clerk values (publishable key, issuer) are owner-gated and
unavailable. Per explicit constraint: do not implement frontend Clerk widgets until required
Clerk values are available and owner-approved.

**Once unblocked (Clerk dev project provisioned + owner approval):**
→ P3-3g: `feat(p3-3): wire @clerk/nextjs ClerkProvider and real getToken integration`

**If Clerk values remain unavailable:**
→ Move to P3-4 (rate limits/abuse protection — safe to plan/implement independently)

---

## 9. Honest limits

- No production enable, no real secrets committed, no `.env` edits, no `@clerk/nextjs` installed.
- No mock auth removed, no local demo broken.
- Backend gates: 576 / frontend: 122 — unchanged (zero code changes this slice).
- The stale comment in `dependencies.py:73-74` ("No-op until platform_admin is added...") is
  incorrect post-P3-3e but deliberately deferred to keep this slice strictly docs-only.
