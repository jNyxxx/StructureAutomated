# ADR - Auth Provider

**Status:** Accepted - Clerk selected
**Date:** 2026-06-22

## Context

Auth/session lifecycle is a launch blocker. The provider choice must be locked before auth implementation starts. A managed provider reduces the primary auth security surface while the application still owns tenant-scoped authorization and access control.

## Decision

Use **Clerk** as the managed auth provider.

Clerk owns credentials, login, primary sessions, password reset, email verification, MFA support, and primary auth security. The application owns tenant membership, RBAC, object authorization, billing gates, support-access approvals, audit logs, tenant context, and database RLS.

Platform-admin MFA remains required before external users or production. Tenant-owner/admin MFA remains strongly recommended.

Do **not** build first-party email/password auth unless a future ADR explicitly reverses this decision.

## Options considered

| Option | Verdict |
|---|---|
| Clerk managed auth | Accepted - fastest production-safe MVP path with provider-owned auth lifecycle |
| Auth0 / Supabase Auth | Rejected for MVP - viable managed alternatives, but not selected by owner |
| First-party email/password | Rejected for MVP - app would own password storage, resets, verification, session security, and auth abuse controls |

## Consequences

- App-side authorization is unchanged: tenant membership, RBAC, object ownership, billing gates, support access, audit, tenant context, and RLS stay in-app.
- App user records store Clerk identity mapping, not password hashes or first-party credential lifecycle state.
- App-side session/revocation records are allowed only where needed for tenant access invalidation, audit, and membership-version enforcement.
- Clerk configuration and platform-admin MFA are launch blockers before external users / production.

## Owner decisions / open questions

- [x] Managed auth provider selected: Clerk.
- [x] First-party email/password excluded from MVP unless a future ADR reverses this decision.
- [ ] Clerk production configuration, domains, templates, and MFA policy must be verified before external users.

## Related docs

[AUTH_AND_RBAC](../AUTH_AND_RBAC.md) - [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) - [CLAUDE](../../CLAUDE.md)
