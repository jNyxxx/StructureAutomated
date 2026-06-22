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

## 8. Required isolation tests

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
