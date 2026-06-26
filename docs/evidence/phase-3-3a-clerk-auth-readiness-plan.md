# Clerk Production Auth Readiness Plan (P3-3a)

**Purpose:** Inspect current authentication implementation and define the production Clerk JWT verification contract, required env/secrets, mock-auth isolation boundaries, test requirements, and implementation slices — without implementing auth code or requiring real Clerk secrets.
**Source sections:** Master guide §3 (auth boundary), §9 (session lifecycle), §10 (credential encryption), §25 (launch blockers)
**Status:** Owner decision needed
**Related docs:** [PHASE_3_IMPLEMENTATION_PLAN](../PHASE_3_IMPLEMENTATION_PLAN.md) · [AUTH_AND_RBAC](../AUTH_AND_RBAC.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [CLAUDE.md](../../CLAUDE.md)

---

## 1. Verdict

**P3-3a (inspection + plan): COMPLETE — 2026-06-26**

Production auth is **planned/deferred, NOT enabled**. Mock auth remains the only live path. No production cutover in this slice. Implementation is gated on owner Clerk configuration decisions (§6).

- Backend DI seam for a real Clerk verifier: **ready** (`ClerkTokenVerifier` Protocol, `AuthService` constructor injection)
- Frontend real Clerk widget: **not wired** (mock stub only; fails closed in `NODE_ENV=production`)
- Boot guard Clerk-specific checks: **not yet added** (gap scoped to P3-3b)
- Real Clerk secrets: **not added**, not required here
- Mock auth safeguards: **unchanged**, must remain

---

## 2. Current auth state

### Backend (`backend/app/auth/`)

| File | Purpose |
|------|---------|
| `verifier.py` | `ClerkTokenVerifier` Protocol + `VerifiedClerkClaims` dataclass + `LocalMockClerkVerifier` (only impl) |
| `principal.py` | `CurrentPrincipal` frozen dataclass — resolved from token + membership |
| `dependencies.py` | FastAPI deps: `bearer_token()`, `selected_tenant_id()`, `auth_service()`, `current_principal()` |
| `local_mock.py` | `build_local_mock_auth_service()` — wired at app startup only when `app_env != production AND mock_verifier` |

**Mock auth path:** `Authorization: Bearer token-sentinel` + `X-Tenant-ID: <uuid>` → `LocalMockClerkVerifier` (hardcoded tokens `"token-sentinel"`, `"fake-valid-token"`) → fixed mock claims → user/membership lookup → `CurrentPrincipal`. No network calls. Fully deterministic.

**`CurrentPrincipal` shape:**
```
provider_user_id, provider_session_ref, user_id, email,
tenant_id, role, membership_version, mfa_verified
```

**Error chain from `current_principal()`:**

| Check | Code | HTTP |
|-------|------|------|
| Missing/malformed `Authorization` | `UNAUTHENTICATED` | 401 |
| Missing/invalid `X-Tenant-ID` | `TENANT_REQUIRED` | 400 |
| Auth service not configured | `AUTH_NOT_CONFIGURED` | 500 |
| Token invalid/expired | `UNAUTHENTICATED` | 401 |
| Session revoked | `AUTH_SESSION_REVOKED` | 401 |
| User not found / deleted | `UNAUTHENTICATED` | 401 |
| No/inactive membership | `TENANT_ACCESS_DENIED` | 403 |

**RBAC:** 7 roles / 14 permissions / default-deny matrix in `services/authz.py`. Object auth via `ObjectAuthorizationService.require_tenant_owner()` (403 `OBJECT_ACCESS_DENIED`).

**Boot guard (production-only) — current auth-relevant behavior:**
- Rejects placeholder `jwt_secret` / `encryption_key` / `webhook_secret`
- Rejects mock providers unless `controlled_demo` + `controlled_demo_approved_by` attestation
- Rejects `secret_backend != "aws"` in production
- Rejects DB role with `SUPERUSER` or `BYPASSRLS`
- **Gap:** no Clerk issuer / JWKS URL / audience validation — to be added in P3-3b

**Test coverage:**
- `test_auth.py` — valid/missing/invalid/revoked token; no-membership/wrong-tenant; mock only non-prod; no raw-token storage
- `test_authz.py` — role-permission matrix; default-deny; object auth; support access lifecycle
- `test_boot_guard.py` — prod gates; 29-table RLS no-drift; controlled_demo; adapter no live-paths

### Frontend (`frontend/lib/clerk.tsx`)

- **Real `@clerk/nextjs`: NOT mounted.** Mock/stub adapter only.
- `NEXT_PUBLIC_CLERK_MOCK_MODE` flag controls real vs mock; `blockedMockState()` fails closed in `NODE_ENV=production`.
- `localMockState.getToken = async () => null` — no token sent in mock mode; mock backend ignores missing token via `LocalMockClerkVerifier`.
- `isLocalMockAuthAllowed()`: `NODE_ENV !== "production" || mockMode in ("true","1")`.
- Token attachment: `lib/api-client.ts authenticatedApiRequest()` sets `Authorization: Bearer <token>` (if token non-null) + `X-Tenant-ID`.
- Tenant ID: `useTenantContext().selectedTenantId` (from `/auth/me` response).

### `.env.example` auth vars (names only)

- `AUTH_PROVIDER=managed`
- `AUTH_PROVIDER_PUBLISHABLE_KEY=CHANGE_ME_PLACEHOLDER`
- `AUTH_PROVIDER_SECRET_KEY=CHANGE_ME_PLACEHOLDER`
- `NEXT_PUBLIC_CLERK_MOCK_MODE` — **not yet in `.env.example`** (runtime-read only; must be added in P3-3b)

---

## 3. Production Clerk verifier contract

Design to implement in P3-3b. No code written here.

### 3.1 New class: `ClerkJwksVerifier`

Implements existing `ClerkTokenVerifier` Protocol (drop-in via existing DI seam):
- `AuthService.__init__(verifier: ClerkTokenVerifier)` — no interface change needed
- `build_local_mock_auth_service()` stays; production wires `ClerkJwksVerifier` instead
- Boot in `main.py` lifespan: instantiate `ClerkJwksVerifier` with settings; wire to `AuthService`

### 3.2 Bearer flow

```
Frontend Clerk session
  → getToken() → short-lived Clerk JWT (RS256, exp ~1h)
  → Authorization: Bearer <jwt>   (+ X-Tenant-ID: <uuid>)
  → ClerkJwksVerifier.verify(token)
  → VerifiedClerkClaims
  → AuthService.resolve_principal(claims, tenant_id)
  → CurrentPrincipal (unchanged downstream contract)
```

### 3.3 JWKS / signature verification

- Fetch JWKS from `${AUTH_PROVIDER_ISSUER}/.well-known/jwks.json` (or `AUTH_PROVIDER_JWKS_URL` if set explicitly)
- Cache keys in memory with TTL (recommended: 1h); on `kid` cache-miss → refresh once before failing
- Verify RS256 signature against matching key `kid`

### 3.4 Claims validation

| JWT claim | Validation | Maps to `VerifiedClerkClaims` |
|-----------|-----------|-------------------------------|
| `iss` | Must equal `AUTH_PROVIDER_ISSUER` exactly | — (validation only) |
| `aud` / `azp` | If `AUTH_PROVIDER_AUDIENCE` / `AUTH_PROVIDER_AUTHORIZED_PARTIES` configured, must match | — (validation only) |
| `exp` | Must be in the future (allow ≤30s leeway) | `expires_at` |
| `sub` | Non-empty string | `provider_user_id` |
| `email` (or template claim) | Non-empty string | `email` |
| `sid` | Session ID string | `provider_session_ref` |
| MFA claim (`amr` or Clerk template flag) | Boolean/present | `mfa_verified` |

No raw token stored anywhere. Claims object carries no secrets (per AUTH_AND_RBAC §5).

### 3.5 Identity → internal mapping

Unchanged: `provider_user_id` → app user via `("clerk", sub)` lookup in existing user store. Full `resolve_principal` chain reused as-is.

### 3.6 Tenant selection

Unchanged: explicit `X-Tenant-ID` header; membership must exist + `tenant_status="active"`; no implicit default; no per-token tenant embedding.

### 3.7 MFA enforcement

- Platform-admin role: enforce `mfa_verified=True` before external users / production (AUTH_AND_RBAC §5); reject request (401) if false
- Tenant-owner / tenant-admin: strongly recommended; enforcement policy to be confirmed by owner (see §6 decision 4)

### 3.8 Failure modes

| Failure | Behavior | HTTP code | Error code |
|---------|----------|-----------|------------|
| Missing `Authorization` header | Fail closed | 401 | `UNAUTHENTICATED` |
| Malformed / expired / bad signature | Fail closed, no token detail leaked | 401 | `UNAUTHENTICATED` |
| `iss` mismatch | Fail closed | 401 | `UNAUTHENTICATED` |
| `aud`/`azp` mismatch (if configured) | Fail closed | 401 | `UNAUTHENTICATED` |
| JWKS endpoint unreachable | Fail closed (5xx, hard error) — **never fall back to mock in production** | 503 | `AUTH_UNAVAILABLE` |
| Unknown / deleted user | Fail closed | 401 | `UNAUTHENTICATED` |
| Session revoked | Fail closed | 401 | `AUTH_SESSION_REVOKED` |
| No / inactive membership | Fail closed | 403 | `TENANT_ACCESS_DENIED` |
| Missing `X-Tenant-ID` | Fail closed | 400 | `TENANT_REQUIRED` |

### 3.9 Boot guard additions (P3-3b scope)

Add to production boot check (auth-specific):
- `AUTH_PROVIDER_ISSUER` present + non-placeholder
- `AUTH_PROVIDER_SECRET_KEY` present + non-placeholder (already partly covered; ensure Clerk-specific var checked)
- `mock_verifier=False` in production (already blocked by mock-provider gate; explicit check for clarity)
- `AUTH_PROVIDER_PUBLISHABLE_KEY` / `NEXT_PUBLIC_CLERK_*` vars non-placeholder if frontend served from same build
- Optional: JWKS endpoint reachable at boot (configurable; log warning if unreachable rather than hard fail, to allow offline staging builds)

---

## 4. Required env/secrets

Naming reuses generic `AUTH_PROVIDER_*` prefix to keep boot guard provider-agnostic.

### 4.1 Backend

| Var | Status | Description |
|-----|--------|-------------|
| `AUTH_PROVIDER` | Exists (`managed`) | Provider type identifier |
| `AUTH_PROVIDER_ISSUER` | **New — required** | Clerk issuer URL (`https://<clerk-domain>`) |
| `AUTH_PROVIDER_JWKS_URL` | **New — optional** | Override JWKS URL; defaults to `{issuer}/.well-known/jwks.json` |
| `AUTH_PROVIDER_AUDIENCE` | **New — optional** | Expected `aud` claim if Clerk JWT template sets it |
| `AUTH_PROVIDER_AUTHORIZED_PARTIES` | **New — optional** | Comma-separated allowed `azp` values |
| `AUTH_PROVIDER_SECRET_KEY` | Exists (placeholder) | Clerk backend/secret key; required + non-placeholder in production |
| `AUTH_PROVIDER_PUBLISHABLE_KEY` | Exists (placeholder) | Clerk publishable key; required in frontend env |

### 4.2 Frontend

| Var | Status | Description |
|-----|--------|-------------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | **New — required** | Clerk publishable key for `@clerk/nextjs` |
| `NEXT_PUBLIC_CLERK_MOCK_MODE` | **Not in .env.example** | Must be added; default unset/false; `true` only for local/dev |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | **New — optional** | Custom sign-in URL if non-default routing used |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | **New — optional** | Custom sign-up URL |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL` | **New — optional** | Redirect after sign-in |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL` | **New — optional** | Redirect after sign-up |

### 4.3 Clerk dashboard (not env vars — configuration side)

- Allowed origins / callback URLs for production app domain
- JWT template (if custom claims: `email`, MFA flag, `sid`)
- MFA policy for platform-admin users
- Webhook signing secret (if session-revocation webhook used)

### 4.4 Secret storage

Per CLAUDE.md §10 + resolved owner decision (AWS Secrets Manager + AWS KMS):
- `AUTH_PROVIDER_SECRET_KEY` in AWS Secrets Manager; Postgres stores no raw secrets
- `AUTH_PROVIDER_ISSUER` / `AUTH_PROVIDER_JWKS_URL` are public values; safe in env or Secrets Manager
- Audience / authorized parties are public; safe in env
- Decrypted values never reach logs, prompts, audits, exports, frontend bundles, or error details

### 4.5 Local/mock separation

- Mock path stays gated on `app_env != production AND mock_verifier`; placeholders fail boot in production (existing)
- Frontend: `isLocalMockAuthAllowed()` blocks real Clerk in production unless explicit flag
- `NEXT_PUBLIC_CLERK_MOCK_MODE=true` must NOT appear in production `.env`; must NOT be committed to production secrets

---

## 5. Implementation slices (P3-3b → P3-3e)

| Slice | Scope | Gate |
|-------|-------|------|
| **P3-3b** | Backend `ClerkJwksVerifier` implementing `ClerkTokenVerifier` Protocol; wired via existing DI seam; extend boot guard with Clerk config/JWKS fail-closed checks; `LocalMockClerkVerifier` unchanged for non-prod; update `.env.example` with new vars | Owner confirms Clerk instance + issuer (§6 decisions 1–2) |
| **P3-3c** | Frontend real `@clerk/nextjs` `ClerkProvider` + `useAuth()`/`getToken()` wired behind `NEXT_PUBLIC_CLERK_MOCK_MODE`; mock remains default for local/test; sign-in/sign-up routing if needed | Depends on P3-3b; owner confirms frontend URLs/routing (§6 decision 2) |
| **P3-3d** | Auth/RBAC end-to-end smoke: real-shaped JWT verify path using test JWKS/keys (no real secrets in CI); membership/tenant isolation; MFA-for-admin; all failure modes; no production cutover | Depends on P3-3b; test JWKS key pair generated for CI |
| **P3-3e** | Evidence doc + `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` update marking Clerk-prod blocker resolved; final readiness assertion | Depends on P3-3b through P3-3d complete + passing |

---

## 6. Owner decisions required before P3-3b

| # | Decision | Recommended default | Needed by |
|---|----------|---------------------|-----------|
| 1 | Which Clerk project/environment to use (prod instance vs dev/preview); separate instances for staging vs production? | Separate prod + dev instances recommended | P3-3b start |
| 2 | Allowed domains + callback/redirect URLs for production app | Determined by production domain choice | P3-3b start |
| 3 | Production tenant/user bootstrap process — how are first user/membership records created (Clerk invite flow, manual DB seed, admin UI, or migration script)? | Manual seed + admin bootstrap script for pilot | P3-3b planning |
| 4 | Platform-admin MFA mandatory at launch? (AUTH_AND_RBAC §5 says "required before external users") | Yes — mandatory | P3-3b |
| 5 | First client onboarding: Clerk invite flow or manual bootstrap? | Manual bootstrap for controlled pilot | P3-3b planning |
| 6 | Who owns Clerk dashboard configuration (keys, JWT templates, MFA policy, domain allow-listing)? | Named owner or ops lead | P3-3b start |

---

## 7. Honest limits

- No real Clerk secrets used in this slice; no Clerk project created or configured here
- `ClerkJwksVerifier` not implemented; DI seam ready but wired to `LocalMockClerkVerifier` only
- Boot guard has no Clerk issuer/JWKS/audience checks — planned gap to close in P3-3b
- Production not enabled; real providers, sending, Stripe, SMS remain deferred
- Frontend real `@clerk/nextjs` not installed or configured; mock stub unchanged
- MFA enforcement at the app layer not yet implemented (requires verifier returning real `mfa_verified`)
- P3-5/P3-6 stop gates unchanged
