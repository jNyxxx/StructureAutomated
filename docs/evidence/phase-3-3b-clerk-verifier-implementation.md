# Clerk JWKS Verifier Implementation (P3-3b)

**Purpose:** Record the backend-only implementation of the production Clerk JWT verification path (`ClerkJwksVerifier`), the production auth boot-guard checks, the MFA enforcement mechanism, deterministic test coverage, and the six owner decisions answered for P3-3b — without enabling production, adding real Clerk secrets, or performing a production cutover.
**Source sections:** Master guide §3 (auth boundary), §9 (session lifecycle), §10 (credential encryption), §25 (launch blockers); builds on [phase-3-3a-clerk-auth-readiness-plan](phase-3-3a-clerk-auth-readiness-plan.md).
**Status:** Complete — 2026-06-26
**Related docs:** [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [AUTH_AND_RBAC](../AUTH_AND_RBAC.md) · [CLAUDE.md](../../CLAUDE.md) · [phase-3-3a-clerk-auth-readiness-plan](phase-3-3a-clerk-auth-readiness-plan.md)

---

## 1. Verdict

**P3-3b: COMPLETE — backend verifier implemented; production NOT enabled / NOT cut over.**

A production-safe Clerk JWT verifier exists behind the existing `ClerkTokenVerifier` Protocol, the boot guard now fails closed on missing/placeholder managed-auth config (and on mock auth in production — even under `controlled_demo`), and an MFA enforcement primitive is implemented and tested. No real Clerk secrets were added, no `.env` was touched, no frontend Clerk widget changed, and the live request chain is unchanged. Full managed-auth service wiring, frontend Clerk, and a real-JWT smoke remain gated to P3-3c→P3-3e.

## 2. Owner decisions recorded (answers to P3-3a §6)

| # | Decision | Owner answer |
|---|----------|--------------|
| 1 | Clerk project/environments | Separate Clerk **Production** project, plus separate **dev/staging** Clerk environments |
| 2 | Production app domain / allowed origins | Canonical: `https://app.automatedstructure.com`. **No** localhost, preview URLs, or wildcards in production |
| 3 | First pilot tenant/user/membership | **Manual bootstrap**, not public signup |
| 4 | Platform-admin MFA at launch | **Mandatory** for `platform_admin` |
| 5 | First client onboarding | **Manual bootstrap**; Clerk invite flow comes later |
| 6 | Clerk dashboard ownership / approvals | **Platform Engineering / DevOps** owns Clerk dashboard config; **Security / CTO** approves MFA + JWT claims; **SaaS owner** approves onboarding + role model |

Mirrored into [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) §2 / §7. Decision #2 (no localhost/preview/wildcard) is enforced by the boot guard for `AUTH_PROVIDER_ISSUER` / `AUTH_PROVIDER_JWKS_URL`.

## 3. Files changed

| File | Change |
|------|--------|
| `backend/app/auth/clerk_jwks.py` | **New.** `ClerkJwksVerifier` (RS256/JWKS), `JwksSource` Protocol, `StaticJwksSource` (tests), `HttpxJwksSource` (prod, TTL cache, lazy httpx), `build_managed_clerk_verifier()` factory |
| `backend/app/auth/mfa.py` | **New.** `mfa_required_roles()` + fail-closed `enforce_mfa()` (403 `MFA_REQUIRED`) |
| `backend/app/config.py` | Added managed-auth settings (`auth_provider`, `auth_provider_issuer`/`_jwks_url`/`_audience`/`_authorized_parties`/`_email_claim`/`_session_claim`/`_mfa_claim`/`_secret_key`/`_publishable_key`, `auth_mfa_required_roles`) |
| `backend/app/observability/boot_guard.py` | Added `_auth_failures()` + `_is_https_nonlocal()`; wired into `config_failures()` |
| `backend/pyproject.toml` | Added runtime deps `httpx>=0.27`, `cryptography>=42` |
| `.env.example` | Added managed-auth placeholders + MFA-roles var (placeholders only; no secrets) |
| `backend/tests/test_clerk_jwks.py` | **New.** ~20 deterministic verifier tests (cryptography-generated keys, in-memory JWKS, fixed clock) |
| `backend/tests/test_mfa.py` | **New.** MFA helper tests |
| `backend/tests/test_boot_guard.py` | Updated `_safe_prod()`; added 8 auth-config/mock-verifier/controlled-demo tests |
| `backend/tests/test_auth.py` | Added "production does not attach mock verifier" test |
| `docs/*` | This evidence + LAUNCH_BLOCKERS + DOCUMENTATION_MANIFEST |

## 4. Verifier implementation summary

`ClerkJwksVerifier` implements the existing `ClerkTokenVerifier` Protocol (drop-in via the `AuthService(verifier=…)` seam — no interface change). RS256 signature verification uses **`cryptography`** only — no PyJWT/jose dependency.

- **JWKS source is injectable** — tests use `StaticJwksSource` (offline, deterministic); production uses `HttpxJwksSource` (HTTPS fetch, 1h TTL cache, httpx imported lazily). On `kid` cache-miss the verifier refreshes the JWKS once before failing.
- **Claim mapping:** `sub`→`provider_user_id`, configured email claim (default `email`)→`email`, configured session claim (default `sid`)→`provider_session_ref`, `exp`→`expires_at`, configured MFA claim (if set)→`mfa_verified`.
- **Validation:** issuer exact-match; `exp` with ≤30s leeway; `aud` (str or list) when configured; `azp` against authorized-parties allowlist when configured; all required claims non-empty.
- **Fails closed** on malformed token, bad signature, expiry, issuer/audience/azp mismatch, missing claims, unknown `kid`, malformed JWKS, and JWKS-unavailable. **Only `alg=RS256` is accepted** — `none`/HMAC are rejected (no alg-confusion). Raw token is never logged, stored, or echoed into error messages. **Never** falls back to the local mock verifier.

## 5. Config / env additions

Backend `Settings` (read from env; no secrets hardcoded): `auth_provider` (default `managed`), `auth_provider_issuer`, `auth_provider_jwks_url`, `auth_provider_audience`, `auth_provider_authorized_parties`, `auth_provider_email_claim` (`email`), `auth_provider_session_claim` (`sid`), `auth_provider_mfa_claim`, `auth_provider_secret_key`, `auth_provider_publishable_key`, `auth_mfa_required_roles` (`platform_admin`). `.env.example` updated with **placeholders only** — `AUTH_PROVIDER_ISSUER=CHANGE_ME_PLACEHOLDER`, keys remain `CHANGE_ME_PLACEHOLDER`. The real `.env` was not read or modified.

## 6. Boot-guard additions (production-only, deterministic, no network)

`_auth_failures()` (part of `config_failures()`, so it gates both API and worker boot) fails closed when, in production:

- `mock_verifier` is true — **controlled_demo does not bypass auth** (the key hardening: controlled_demo may still permit mock billing/mailbox/dns/research, never mock auth).
- `auth_provider` is not a managed provider (`managed`/`clerk`).
- `AUTH_PROVIDER_ISSUER` is blank/placeholder, or not an https non-localhost URL (decision #2).
- `AUTH_PROVIDER_JWKS_URL`, if set, is not an https non-localhost URL.
- `AUTH_PROVIDER_SECRET_KEY` or `AUTH_PROVIDER_PUBLISHABLE_KEY` is blank/placeholder.

**JWKS reachability is intentionally not boot-checked** (no network at boot, per the readiness plan); it is a documented runtime/manual verification before cutover. The non-network config validation is fully covered by tests.

## 7. MFA enforcement status

Mechanism implemented and tested (`enforce_mfa()` → 403 `MFA_REQUIRED`; `mfa_required_roles()` defaults to `platform_admin`). **It is intentionally NOT attached to `current_principal`**: `platform_admin` is **not** in the RBAC matrix (`services/authz.py` defines 7 roles: owner, admin, marketer, reviewer, viewer, billing_admin, support). Per the P3-3b constraint "do not invent a new role model," enforcement stays inert until the role is added; tests prove the mechanism against the available role path (e.g. an `admin` placed in the required set is blocked without MFA; tenant owner/admin outside the set are never weakened). **Honoring owner decision #4 fully requires adding `platform_admin` to RBAC and wiring `enforce_mfa()` — tracked as a remaining blocker.**

## 8. Tests added/updated

- `test_clerk_jwks.py` — valid→claims mapping; MFA true/false/absent; bad signature; expired; within-leeway; wrong issuer; audience (str+list) enforced; azp enforced; missing `sub`/`email`/`sid`/`exp`; unknown kid; malformed JWKS; non-RS256 (`none`/HS256/RS512) rejected; malformed token shapes; kid-miss→refresh→success; JWKS-unavailable fail-closed; error messages never leak the raw token; factory build + issuer-required.
- `test_mfa.py` — default required roles; comma-list parse; required-role-without-MFA blocked (403 `MFA_REQUIRED`); with-MFA passes; unlisted role never forced; empty set no-op.
- `test_boot_guard.py` — `_safe_prod()` extended with managed-auth config; missing/placeholder/non-https/localhost issuer; bad JWKS URL (and default-ok); placeholder secret/publishable keys; non-managed provider; `mock_verifier` in prod; **controlled_demo + attestation + mock_verifier still fails** (no auth bypass).
- `test_auth.py` — production env does not attach the mock verifier.

## 9. Gate results (2026-06-26)

| Gate | Result |
|------|--------|
| `ruff check app tests` | PASS (All checks passed) |
| `black --check app tests` | PASS (195 files unchanged) |
| `mypy app --ignore-missing-imports` | PASS (no issues, 147 files) |
| `pytest` | **566 passed** |
| frontend `npm run lint` | PASS (no ESLint warnings/errors) |
| frontend `npm run typecheck` | PASS (`tsc --noEmit`) |
| frontend `npm run test` | **122 passed** |
| frontend `npm run build` | PASS (compiled, static prerender) |

## 10. Safety confirmation

- Production not enabled; no production cutover. No real Clerk secrets added; `.env` untouched. No frontend Clerk widget changed.
- Local/mock auth unchanged and remains non-production only (`app_env != production AND mock_verifier`).
- `current_principal` / `AuthService` chain, membership/RBAC checks, `X-Tenant-ID` selection, RLS, and tenant isolation all unchanged. No protected route made public.
- No real providers / sending / Stripe / SMS / live scraping enabled. P3-4/P3-5/P3-6 not started. No deploy.

## 11. Remaining blockers before production cutover

1. **Real Clerk Production project + values** (issuer/JWKS/secret/publishable) sourced from AWS Secrets Manager — not added here.
2. **Managed `AuthService` wiring** — `ClerkJwksVerifier` + `build_managed_clerk_verifier()` are ready, but a production `AuthService` needs request-scoped DB-backed user/membership/session stores (identity lookup before tenant context vs membership lookup under RLS). `main.py` currently wires only the non-prod mock service; production leaves auth unconfigured (fail-closed). → P3-3c+.
3. **`platform_admin` role** not in RBAC — add it, then wire `enforce_mfa()` to satisfy owner decision #4.
4. **Frontend real `@clerk/nextjs`** (`ClerkProvider`/`getToken`) behind `NEXT_PUBLIC_CLERK_MOCK_MODE` — P3-3c.
5. **JWKS reachability + real-JWT smoke** — runtime/manual verification + P3-3d CI smoke with test keys.
6. **JWKS-unavailable maps to 401** (fail-closed via `TokenVerificationError`) rather than the readiness plan's distinct 503 `AUTH_UNAVAILABLE`; the dedicated 503 mapping is deferred (would require an `AuthService` error-path change).
