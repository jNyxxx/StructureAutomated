# ADR — Auth Provider

**Status:** Proposed — **Owner decision needed** (must be locked before any auth coding)
**Date:** 2026-06-22

## Context

Auth/session lifecycle is a launch blocker. The provider choice must be locked before auth implementation starts. Regardless of provider, the **application** always owns tenant membership, RBAC, object authorization, audit logging, and billing/usage gates — the provider only handles identity/session primitives.

## Decision

**Not final.** Recommended default from the guide (a default, not a committed decision): **managed auth** (e.g., Clerk, Auth0, or Supabase Auth) for the fastest production-safe MVP.

First-party email/password auth is permitted **only if** the team implements and tests the full lifecycle: Argon2id (or bcrypt cost 12) hashing, email verification, 15-minute access tokens, 14-day rotating refresh tokens, reuse detection, revocation, reset tokens, session table, admin MFA, rate limits, secure cookies, and security audit events.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Managed auth** (recommended default) | Fast, smaller security surface, lifecycle handled by vendor | Vendor dependency/cost; must still map sessions → tenant membership in-app |
| **First-party email/password** | Full control, no vendor lock-in | Team owns and must test the entire security lifecycle; higher risk if incomplete |

## Consequences

- App-side authorization (membership, RBAC, object ownership, billing gates, audit) is unchanged either way — see [AUTH_AND_RBAC](../AUTH_AND_RBAC.md).
- **MFA is a launch blocker for platform admins** in both options.
- If managed: implement session→tenant mapping and revocation hooks.
- If first-party: the full lifecycle above becomes mandatory, tested scope before launch.

## Owner decisions / open questions

- [ ] **Final provider choice** (managed vs first-party) — owner decision needed.
- [ ] If first-party: confirm owner/team accountable for the full security lifecycle + tests.

## Related docs

[AUTH_AND_RBAC](../AUTH_AND_RBAC.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [CLAUDE](../../CLAUDE.md)
