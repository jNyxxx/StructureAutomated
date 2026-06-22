# Auth & RBAC

**Purpose:** Auth/session lifecycle, RBAC roles + permission matrix, object authorization, tenant isolation (HTTP + worker context), and platform/support access. The auth **provider** choice is controlled by an ADR (below) — do not implement auth until it is locked.
**Source sections:** Master guide §3 (users/roles/authz), §8 (tenant isolation, support access), §9 (auth/session lifecycle).
**Status:** Draft (auth provider = **Owner decision needed**)
**Related docs:** [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) (provider decision) · [CLAUDE](../CLAUDE.md) (rules 1–6) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (`sessions`, tokens, RLS) · [API_CONTRACT](API_CONTRACT.md) (auth routes) · [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) (isolation tests)

---

## 1. Auth provider decision

**Locked by [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) before any auth coding.** — **Needs owner decision.**

- Recommended MVP default: **managed auth** (Clerk/Auth0/Supabase Auth) with tenant membership, RBAC, object authorization, audit logs, and billing gates still owned by the application.
- First-party email/password allowed **only** if the team implements + tests the full lifecycle below (hashing, verification, short access tokens, rotating refresh tokens, reuse detection, revocation, reset, session table, admin MFA, rate limits, secure cookies, security audit events).

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

1. Authenticated session.
2. Active tenant membership.
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

## 5. Session lifecycle

### Signup
- Validate email + password strength. Hash with **Argon2id** (preferred) or bcrypt cost 12 if standardized.
- Create user with `email_verified_at = NULL`; create tenant + owner membership only through onboarding; send verification email.
- External users cannot run campaigns until email verified. Production password minimum **12 chars**. Rate-limit by IP + email.

### Login & tokens
Flow: rate-limit (IP+email) → verify hash → reject deleted → require verification if enabled → MFA challenge for admins/owners if enabled → create session → issue tokens → store refresh **hash only** → audit success/failure.

| Token | Lifetime | Storage | Notes |
|---|---|---|---|
| Access | 15 min | Memory or secure cookie | user_id, session_id, tenant_id (optional), roles version; no secrets. |
| Refresh | 14 days | HttpOnly Secure SameSite cookie | Raw token never stored; **rotate every refresh**. |
| Email verification | 24 h | DB hash | One-time use. |
| Password reset | 30 min | DB hash | One-time use; revokes sessions on success. |

### Refresh rotation & reuse detection
Hash incoming token → find active session by hash → **if not found but family was rotated before → treat as reuse attack: revoke entire token family, emit security alert/audit, force login** → if valid, issue new refresh token, store hash, rotate old session, return new access token.

### Revocation, reset, MFA, deletion
- Logout current → revoke current session. Logout all → revoke all user sessions.
- Password reset → revoke all sessions. Role change → increment membership version, force token refresh.
- Tenant lock/deletion → invalidate tenant access immediately.
- **MFA is a launch blocker for platform admins**; strongly recommended for tenant owners/admins.
- Deletion/export must handle user, tenant, research snippets, embeddings, uploads, exports — **no ad-hoc SQL** (see [PRIVACY_AND_RETENTION](PRIVACY_AND_RETENTION.md)).

## 6. Tenant isolation

### HTTP request context
1. Validate access token → 2. Resolve session → 3. Resolve tenant membership (route/header/subdomain) → 4. Check tenant status + subscription access → 5. Open DB via tenant helper → 6. `SET LOCAL app.current_tenant_id = '<tenant_id>'` in transaction → 7. Query through repositories only → 8. Release connection.

```python
async with tenant_db.session(tenant_id=tenant_id, actor_id=user_id, request_id=request_id) as conn:
    await contact_repo.list_contacts(conn, filters)
```

### Worker context (security view)
Every tenant job payload must include: `tenant_id`, `actor_user_id` or `system_actor`, `correlation_id`, `job_id`, `idempotency_key`, `requested_permission`. Worker must **fail closed** if tenant context is missing, set context through the same helper, then **re-check subscription, usage, permission, object access** before executing. Full job lifecycle → [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md).

## 7. Platform & support access

- Platform routes under `/api/v1/platform/*`; require platform role + audit logging.
- Support access requires `admin_support_access` grant: reason, scope, approver, start time, expiry, revoke path.
- **Default support grant duration: 60 minutes.** Support actions log `support_access_id`.
- Support **cannot** view secrets, raw credentials, full payment details, or unredacted PII unless scoped + approved.
- Break-glass requires super admin, reason, incident ID, post-incident review.

## 8. Required isolation tests

With Tenant A/B fixtures (users, roles, contacts, prospects, campaigns, drafts, agent runs, billing, jobs, audit), prove:

- [ ] Tenant A cannot read/mutate Tenant B objects by UUID guessing.
- [ ] Tenant A cannot access Tenant B billing/audit/drafts/campaigns/prospects/contacts/jobs/agent runs.
- [ ] Workers fail without tenant context.
- [ ] Workers cannot process Tenant B job under Tenant A context.
- [ ] Support access fails without an active grant.
- [ ] Every support access action emits an audit event.

Consolidated suites → [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md).
