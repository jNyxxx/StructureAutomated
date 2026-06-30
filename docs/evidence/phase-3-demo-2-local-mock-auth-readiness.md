# Phase 3 Demo-2: Local/Mock Demo Login Readiness

**Date:** 2026-06-30
**Status:** Complete
**Scope:** Fix local/mock demo login — add "Continue with Demo Account" button so browser demo is usable without real Clerk credentials
**Production status:** NOT enabled
**Provider status:** Real Clerk NOT wired; no real secrets; no real sending; no Stripe money movement; no production deployment; no AWS provisioned

---

## 1. Problem statement

P3-Demo-1 claimed the browser demo was ready. Manual browser testing found the sign-in page showed a dead Clerk shell with no way to log in — the disabled sign-in button leads nowhere and there are no real Clerk credentials available for local/mock mode. P3-Demo-2 fixes this without touching production auth.

Two root causes identified:

1. `ClerkFrontendProvider` was a static value provider — no sign-in action existed.
2. `TenantProvider` calls `GET /auth/me` with `X-Tenant-ID` header seeded from `selectedTenantId`, which starts as `null`. Backend returns 400 if `X-Tenant-ID` is missing, blocking the tenant session from resolving.

---

## 2. Preflight

Tree clean at start of session. All gates green before changes.

---

## 3. Implementation — files changed

### 3.1 `frontend/lib/clerk.tsx` — stateful mock auth provider

**Added exported constants:**
- `MOCK_DEMO_TOKEN = "token-sentinel"` — matches backend `LocalMockClerkVerifier` sentinel
- `MOCK_DEMO_USER_ID = "11111111-1111-1111-1111-111111111111"` — seeded demo user
- `MOCK_DEMO_TENANT_ID = "22222222-2222-2222-2222-222222222222"` — seeded demo tenant
- `MOCK_DEMO_EMAIL = "owner@example.com"` — seeded demo email
- `MOCK_SESSION_KEY = "as_mock_session"` — localStorage key for session persistence

**Added `MockAuthProvider` component:** Stateful provider with `useState`/`useEffect`/`useCallback`/`useMemo`. Reads localStorage in `useEffect` (SSR-safe). Exposes `mockSignIn()` (sets localStorage + state), `mockSignOut()` (clears localStorage + state). Signed-in state yields full demo identity + `"token-sentinel"` token. Unsigned state yields null identity. Production guard: `isLocalMockAuthAllowed()` check blocks both `mockSignIn` and state exposure in production without explicit flag.

**Changed `ClerkFrontendProvider`:** Conditional JSX return (no hooks in outer component — avoids Rules of Hooks violation). If `value` prop provided → static passthrough (existing test/integration use). If no `value` → renders `MockAuthProvider`.

**Added to `FrontendAuthState` interface:** `tenantId?: string | null`, `mockSignIn?: () => void`, `mockSignOut?: () => void`.

### 3.2 `frontend/components/public/auth-card.tsx` — demo login button

Added `"use client"` directive. Added `useFrontendAuth()` call. Added `showDemoLogin` flag: `mode === "login" && auth.mode === "local_mock" && typeof auth.mockSignIn === "function"`. When flag is true, renders divider + secondary `"Continue with Demo Account"` button + caption. Button calls `auth.mockSignIn?.()` then `window.location.href = "/dashboard"` (avoids Next.js router context dependency). Flag is false in production (mock mode not allowed) and on any non-login page.

### 3.3 `frontend/lib/tenant-context.tsx` — X-Tenant-ID seed fix

Added `useEffect` after `selectedTenantId` state declaration:
```typescript
useEffect(() => {
  if (!selectedTenantId && auth.tenantId) {
    setSelectedTenantId(auth.tenantId);
  }
}, [auth.tenantId, selectedTenantId]);
```
This syncs `auth.tenantId` (available after localStorage hydration in `MockAuthProvider`) into `selectedTenantId` before the first `/auth/me` call. Without this, `selectedTenantId` is `null` at mount time and the backend rejects with 400 (missing `X-Tenant-ID` header).

### 3.4 `.env.example` — documentation

Added `NEXT_PUBLIC_CLERK_MOCK_MODE=true` with comment explaining local/mock demo auth use.

---

## 4. What was NOT changed

- Backend: unchanged. `LocalMockClerkVerifier`, `selected_tenant_id()` dependency, `/auth/me` — all untouched.
- No real Clerk credentials added.
- No production JWT cutover.
- No `.env` files (only `.env.example`).
- No real sending enabled.
- No Stripe money movement.
- No deployment.
- No AWS provisioning.
- Boot guard: not weakened. `controlled_demo` still does NOT bypass auth. Mock verifier still hard-blocked in production.
- Tenant/RLS/RBAC/security gates: all unchanged.

---

## 5. Mock auth identity

| Field | Value |
|---|---|
| Token | `token-sentinel` |
| User ID | `11111111-1111-1111-1111-111111111111` |
| Tenant ID | `22222222-2222-2222-2222-222222222222` |
| Email | `owner@example.com` |
| Role | `owner` |

All values match existing backend seed data and `LocalMockClerkVerifier` behavior.

---

## 6. Tests

### New: `frontend/lib/__tests__/clerk.test.tsx` (12 tests)

- `isLocalMockAuthAllowed()`: development, test, undefined NODE_ENV → allowed; production without flag → blocked; production with `NEXT_PUBLIC_CLERK_MOCK_MODE=true` → allowed; production with `NEXT_PUBLIC_CLERK_MOCK_MODE=1` → allowed; production with arbitrary value → blocked.
- `ClerkFrontendProvider` value override passthrough.
- `MockAuthProvider` initial state (isSignedIn=false before hydration).
- `MockAuthProvider` exposes `mockSignIn`/`mockSignOut` in non-production.
- `mockSignIn` sets `isSignedIn=true` with correct demo identity (userId, email, tenantId, mode).
- `mockSignIn` token resolves to `MOCK_DEMO_TOKEN`.
- `mockSignOut` returns to signed-out state (userId/tenantId null).
- `mockSignIn` persists to localStorage.
- `mockSignOut` removes from localStorage.
- Hydrates from localStorage — mounts as signed-in if session key present.
- `AuthGate` production block (shows block message, hides protected content).

### Updated: `frontend/app/__tests__/pages.test.tsx` (+2 tests, 74 total)

- Login page shows demo login button in local/mock mode after hydration.
- Login page does not show demo login button when `mockSignIn` is absent.

---

## 7. Gate results

| Gate | Result |
|---|---|
| Frontend lint | PASS |
| Frontend typecheck | PASS |
| Frontend tests | PASS (74 tests) |
| Frontend build | PASS |
| Backend tests | PASS (638 tests — no backend changes) |

---

## 8. Security / invariant confirmation

- Mock auth blocked in production: `isLocalMockAuthAllowed()` returns `false` when `NODE_ENV === "production"` and `NEXT_PUBLIC_CLERK_MOCK_MODE` is not `"true"` or `"1"`.
- Boot guard unchanged: `LocalMockClerkVerifier` still blocked in production via backend boot guard.
- `controlled_demo` attestation still does NOT bypass auth.
- Tenant isolation: unchanged. `X-Tenant-ID` header now correctly seeded from `auth.tenantId` (mock identity) so backend scopes correctly.
- No weakening of RLS, tenant context, object auth, billing gates, send gate, or rate limits.
- No real secrets in code, logs, git, or client responses.

---

## 9. Demo login flow (local/mock)

1. Ensure local stack running: `docker compose up` (or backend + frontend separately).
2. Navigate to `http://localhost:3000/login`.
3. Click "Continue with Demo Account".
4. Redirected to `/dashboard` as `owner@example.com` / tenant `22222222-2222-2222-2222-222222222222`.
5. Full demo available. Session persists in localStorage (`as_mock_session=1`).
6. Sign out clears localStorage and returns to signed-out state.
