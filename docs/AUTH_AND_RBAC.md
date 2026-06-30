# Auth & RBAC

**Purpose:** Clerk-managed auth boundary, RBAC roles + permission matrix, object authorization, tenant isolation (HTTP + worker context), and platform/support access.
**Source sections:** Master guide §3 (users/roles/authz), §8 (tenant isolation, support access), §9 (auth/session lifecycle).
**Status:** Draft (auth provider = Clerk selected -> [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md))
**Related docs:** [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) (provider decision) - [CLAUDE](../CLAUDE.md) (rules 1-6) - [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (identity mapping, RLS) - [API_CONTRACT](API_CONTRACT.md) (auth routes) - [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) (isolation tests)

---

## 1. Auth provider boundary

Use **Clerk** as the managed auth provider.

Clerk owns credentials, login, primary sessions, password reset, email verification, MFA support, and primary auth security. The application owns tenant membership, RBAC, object authorization, billing gates, support-access approvals, audit logs, tenant context, and database RLS.

Do **not** build first-party email/password auth unless a future ADR reverses this decision.

Platform-admin MFA remains required before external users or production. Tenant-owner/admin MFA remains strongly recommended.

## 2. Core users

| User | Purpose |
|---|---|
| Platform super admin | Owns the SaaS; creates tenants; break-glass only with audit. |
| Platform support admin | Supports tenants only via approved, time-limited grants. |
| Tenant owner | Owns account, billing, users, campaigns, integrations, settings. |
| Tenant admin | Manages team, prospects, campaigns, review queue, deliverability, settings. |
| Marketer | Imports prospects, runs campaigns, reviews performance. |
| Reviewer | Reviews/edits/approves/rejects drafts. |
| Viewer | Reads dashboards/reports only. |
| Billing admin | Manages subscription/invoices/payment/plan if separated from owner/admin. |

## 3. Authorization rule

Frontend role checks are **UX only**. Backend must enforce on every protected action:

1. Authenticated Clerk session.
2. Active app tenant membership.
3. Role/action permission.
4. **Object ownership within tenant** (blocks IDOR).
5. Billing/feature/usage access.
6. Audit logging for sensitive actions.

RLS is the final guardrail, not the only one (CLAUDE rule 6).

## 4. Role capability matrix

| Capability | Owner | Admin | Marketer | Reviewer | Viewer | Billing admin |
|---|---|---|---|---|---|---|
| Dashboard/report read | Yes | Yes | Yes | Limited | Yes | Billing only |
| Prospect/contact import | Yes | Yes | Yes | No | No | No |
| Campaign create/run | Yes | Yes | Yes | No | No | No |
| Draft review/edit/approve | Yes | Yes | Optional | Yes | No | No |
| Send scheduling | Yes | Yes | Role-based | No direct send | No | No |
| Team/role management | Yes | Yes, limited | No | No | No | No |
| Billing management | Yes | No by default | No | No | No | Yes |
| Audit log read | Yes | Admin-level | No | No | No | Billing events only |
| Integration credentials | Yes | Yes, limited | No | No | No | No |

### platform_admin role (decision resolved P3-3d 2026-06-28)

`platform_admin` is stored in the existing tenant-scoped membership model for MVP, but its permissions are limited to explicit platform/admin routes and do not grant implicit tenant data access, RLS bypass, or tenant-owner powers.

| Capability | platform_admin |
|---|---|
| Platform routes (`/api/v1/platform/*`) | Yes |
| Platform health/ops read | Yes |
| Support-grant oversight | Yes |
| Tenant data read (without active support grant) | **No** |
| RLS bypass | **No** |
| Tenant membership/ownership bypass | **No** |
| Implicit tenant owner/admin powers | **No** |

MFA: **mandatory** before external users / production (owner decision, LAUNCH_BLOCKERS §2 #4).

Storage model: `platform_admin` is added to `tenant_memberships.role` (CHECK constraint update + migration). Principal resolution is identical to tenant roles — `principal.role = "platform_admin"` is loaded from the selected tenant membership. The already-wired `enforce_mfa()` in `auth/dependencies.py` activates automatically with zero enforcement code change. Cross-tenant operations still require an active time-boxed support grant via `SupportAccessService`.

Why Option A (tenant-scoped over a separate global table): activates the wired-and-tested `enforce_mfa()` primitive (which keys off `principal.role`) without restructuring principal resolution. A separate `users.is_platform_admin` model would require principal-resolution changes and new enforcement paths — deferred complexity not needed for MVP.

**`support` role drift (pre-existing, flagged):** `ROLE_PERMISSIONS` in `services/authz.py` defines a `support` role, but it is absent from `models/membership.py ROLES` tuple and the `tenant_memberships` CHECK constraint — rows with `role='support'` cannot be inserted into the DB. Live support access uses the grant-based `SupportAccessService` (time-boxed, 60-min default, audited), not a membership role. The `support` entry in `ROLE_PERMISSIONS` is vestigial. Reconciled in the P3-3e migration alongside `platform_admin`.

## 5. App-side session and tenant binding

The app validates Clerk session/token state, resolves the app user by Clerk identity mapping, then resolves tenant membership. App-side session/revocation state is minimal and exists only for tenant access invalidation, audit, and membership-version enforcement.

The app must not store raw Clerk tokens, passwords, password reset tokens, or email verification tokens.

App lifecycle responsibilities:

- Logout/logout-all revoke app-side access records where needed.
- Role change increments membership version and forces re-auth/refresh of app authorization state.
- Tenant lock/deletion invalidates tenant access immediately.
- Platform-admin MFA is verified through Clerk before external users / production.
- Auth-sensitive endpoints and session exchange are rate-limited.
- Security events are audited without secrets or raw tokens.

## 6. Tenant isolation

### HTTP request context

1. Validate Clerk session/token.
2. Resolve app user.
3. Resolve tenant membership from route/header/subdomain.
4. Check tenant status + subscription access.
5. Open DB via tenant helper.
6. `SET LOCAL app.current_tenant_id = '<tenant_id>'` in transaction.
7. Query through repositories only.
8. Release connection.

```python
async with tenant_db.session(tenant_id=tenant_id, actor_id=user_id, request_id=request_id) as conn:
    await contact_repo.list_contacts(conn, filters)
```

### Worker context

Every tenant job payload must include: `tenant_id`, `actor_user_id` or `system_actor`, `correlation_id`, `job_id`, `idempotency_key`, `requested_permission`. Worker must **fail closed** if tenant context is missing, set context through the same helper, then **re-check subscription, usage, permission, object access** before executing. Full job lifecycle -> [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md).

## 7. Platform & support access

- Platform routes under `/api/v1/platform/*`; require platform role + audit logging.
- Support access requires `admin_support_access` grant: reason, scope, approver, start time, expiry, revoke path.
- **Default support grant duration: 60 minutes.** Support actions log `support_access_id`.
- Support **cannot** view secrets, raw credentials, full payment details, or unredacted PII unless scoped + approved.
- Break-glass requires super admin, reason, incident ID, post-incident review.
- The platform role is `platform_admin` — see §4 for the permission boundary and storage model.

## 8. Frontend auth layer

### Adapter contract

The frontend uses a custom `FrontendAuthState` interface (`frontend/lib/clerk.tsx:9`) as an adapter boundary. All app code consumes this interface — not `@clerk/nextjs` directly — so the real Clerk provider can be injected without touching downstream components.

```typescript
interface FrontendAuthState {
  isLoaded: boolean;
  isSignedIn: boolean;
  userId: string | null;
  email: string | null;
  getToken: () => Promise<string | null>;  // same signature as Clerk's getToken()
  mode?: "real_clerk" | "local_mock";
}
```

### ClerkFrontendProvider injection point

`ClerkFrontendProvider` (`frontend/lib/clerk.tsx:55`) accepts `value?: FrontendAuthState`. When `value` is supplied, the internal mock logic is bypassed and the injected state is used directly. When absent, it defaults to `{isSignedIn: false, getToken: async () => null, mode: "local_mock"}`.

Real Clerk wiring (`@clerk/nextjs` not yet installed — P3-3f) adds a wrapper:
- `RealClerkProvider` mounts `<ClerkProvider>` from `@clerk/nextjs` and maps `useAuth()`/`useUser()` to `FrontendAuthState`, passing it as `value` to the existing `ClerkFrontendProvider`.
- Root `layout.tsx` conditionally mounts `RealClerkProvider` when `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is present; otherwise keeps the existing mock provider.
- Mock mode is fully preserved when the key is absent — local demo is unaffected.

### getToken() → API client

`api-client.ts:AuthenticatedApiClientOptions.getToken: () => Promise<string|null>` already matches Clerk's `getToken()` signature. `TenantProvider` passes `auth.getToken` to all backend calls. No downstream changes are needed when real Clerk is wired.

### Tenant context after login

After real Clerk sign-in, `TenantProvider` calls `/auth/me` with `X-Tenant-ID`. If no tenant is pre-selected (null), the backend returns `400 TENANT_REQUIRED`. A tenant-selector step is required between sign-in and the `(app)` route group. Deferred — see `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md §7` (owner decision: auto-select vs explicit selector).

### Local/Mock Demo Auth (P3-Demo-2)

When `NODE_ENV !== "production"` or `NEXT_PUBLIC_CLERK_MOCK_MODE=true`, the `MockAuthProvider` is active. It exposes `mockSignIn()` and `mockSignOut()` through `FrontendAuthState`. The sign-in page (`/login`) accepts the following fixed demo credentials:

| Field | Value |
|---|---|
| Email | `test@example.com` |
| Password | `password` |

Entering these credentials calls `mockSignIn()` and navigates to `/dashboard`. Incorrect credentials display a validation error; no redirect occurs. The one-click "Continue with Demo Account" bypass button has been removed.

Demo identity (matches backend seed data and `LocalMockClerkVerifier`):

| Field | Value |
|---|---|
| Token | `token-sentinel` |
| User ID | `11111111-1111-1111-1111-111111111111` |
| Tenant ID | `22222222-2222-2222-2222-222222222222` |
| Email | `owner@example.com` |
| Role | `owner` |

Session persists in localStorage (`as_mock_session=1`). The `TenantProvider` seeds `selectedTenantId` from `auth.tenantId` via a `useEffect` after localStorage hydration, so the first `/auth/me` call includes the correct `X-Tenant-ID` header.

**Production safety:** `isLocalMockAuthAllowed()` blocks mock auth when `NODE_ENV === "production"` and `NEXT_PUBLIC_CLERK_MOCK_MODE` is not `"true"` or `"1"`. `AuthGate` shows a production block message; no demo content is reachable. Boot guard blocks `LocalMockClerkVerifier` in production regardless. `controlled_demo` does NOT bypass auth.

See [evidence/phase-3-demo-2-local-mock-auth-readiness.md](evidence/phase-3-demo-2-local-mock-auth-readiness.md).

### Mock / production behavior

| State | `mode` | `isLocalMockAuthAllowed()` | Result |
|---|---|---|---|
| Local dev, no key | `local_mock` | true | Mock runs; credential login on sign-in page (`test@example.com` / `password`) |
| Production, no key, no mock flag | `local_mock` | false | `AuthGate` and `ClerkAuthCard` fail closed |
| Production, real key | `real_clerk` | — | Real Clerk session |

### Required isolation tests

`frontend/app/(app)/layout.tsx:11` — `AuthGate` blocks unauthenticated users (client-side). No `middleware.ts` exists; server-side protection via `clerkMiddleware` is deferred to post-smoke hardening.

## 9. Required isolation tests

With Tenant A/B fixtures (users, roles, contacts, prospects, campaigns, drafts, agent runs, billing, jobs, audit), prove:

- [ ] Tenant A cannot read/mutate Tenant B objects by UUID guessing.
- [ ] Tenant A cannot access Tenant B billing/audit/drafts/campaigns/prospects/contacts/jobs/agent runs.
- [ ] Workers fail without tenant context.
- [ ] Workers cannot process Tenant B job under Tenant A context.
- [ ] Support access fails without an active grant.
- [ ] Every support access action emits an audit event.
- [ ] Clerk identity maps to exactly one app user through provider identity fields.
- [ ] No first-party password/reset/verification secret is stored by the app.

Consolidated suites -> [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md).
