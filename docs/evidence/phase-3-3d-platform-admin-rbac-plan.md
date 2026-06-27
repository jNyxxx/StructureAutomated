# P3-3d — platform_admin RBAC & MFA Enforcement Decision

**Purpose:** Record the role-model inspection findings, the resolved `platform_admin` owner decision (Option A), and the P3-3e implementation specification. Docs-only slice — no code, migration, or tests written.
**Status:** Complete (docs-only). Implementation in P3-3e (unblocked, requires explicit approval).
**Related docs:** [AUTH_AND_RBAC](../AUTH_AND_RBAC.md) §4 · [LAUNCH_BLOCKERS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) §2/§6/§7 · [phase-3-3c-managed-auth-wiring.md](phase-3-3c-managed-auth-wiring.md)

---

## 1. Git state

- Branch: `master`
- HEAD at slice start: `e62e55c` (P3-3c managed Clerk auth wiring)
- HEAD at slice end: committed below with only doc changes
- Backend gates: 570 (unchanged — no code modified)
- Frontend gates: 122 (unchanged — no code modified)

---

## 2. Role model findings — 3 canonical sources, with drift

| Source | File | Roles present |
|---|---|---|
| RBAC permission map | `backend/app/services/authz.py:32-83` (`ROLE_PERMISSIONS`) | 7: owner, admin, marketer, reviewer, viewer, billing_admin, **support** |
| ORM model tuple | `backend/app/models/membership.py:21` (`ROLES`) | 6 — **missing `support`** |
| DB CHECK constraint | `backend/migrations/versions/0002_core_tenancy.py:107-110` (`ck_tenant_memberships_role`) | 6 — **missing `support`** |

Exact constraint SQL (`0002_core_tenancy.py:107-110`):
```sql
CHECK (role IN ('owner','admin','marketer','reviewer','viewer','billing_admin'))
```

Constraint is a **literal SQL string**, not a PostgreSQL enum type — adding a value requires a migration (DROP + recreate constraint).

### Role scoping

Roles are **tenant-scoped**: `CurrentPrincipal.role` (`backend/app/auth/principal.py:14-24`) is loaded per-request from `tenant_memberships` for the `X-Tenant-ID`-selected tenant (`backend/app/services/auth.py:100-137`). A user can hold different roles in different tenants.

Authorization gate: `RBACService.has_permission` / `.require` (`authz.py:91-99`) — dict lookup in `ROLE_PERMISSIONS`, default-deny on unknown role.

### `support` role drift (pre-existing)

`support` is in `ROLE_PERMISSIONS` (`authz.py:82`: `"support": frozenset({CAN_USE_SUPPORT_ACCESS})`), but absent from `models/membership.py:21` `ROLES` tuple and from the DB CHECK constraint. Rows with `role='support'` cannot be inserted into `tenant_memberships`.

Live support access uses the grant-based `SupportAccessService` (`authz.py:177-273`, table `support_access_grants`, 60-min default TTL, audited) — not a membership role. The `support` entry in `ROLE_PERMISSIONS` is vestigial. Reconciled in the P3-3e migration alongside `platform_admin`.

---

## 3. MFA mechanism findings

`enforce_mfa(principal, *, required_roles)` (`backend/app/auth/mfa.py:27-37`):

```python
def enforce_mfa(principal: CurrentPrincipal, *, required_roles: frozenset[str]) -> None:
    if principal.role in required_roles and not principal.mfa_verified:
        raise AppError("MFA_REQUIRED", "Multi-factor authentication is required for this role.", status_code=403)
```

- Wired at `backend/app/auth/dependencies.py:75` in `current_principal` (every authenticated request).
- Default `auth_mfa_required_roles="platform_admin"` (`config.py:62-65`).
- No-op at runtime: `platform_admin` absent from RBAC → condition never true → no requests blocked.
- Cannot weaken existing tenant roles: `enforce_mfa` only raises for roles in `required_roles`; the 7 current roles are not in the set.

### MFA claim flow

`auth_provider_mfa_claim` defaults to `None` → `clerk_jwks.py:209`:
```python
mfa_verified = bool(payload.get(self._mfa_claim)) if self._mfa_claim is not None else False
```
→ `mfa_verified` always `False` when claim is `None` (safe/fail-closed default).

Production will set `auth_provider_mfa_claim` (e.g. `"mfa"`) via Secrets Manager/env after Clerk JWT template is configured. No change to verifier code needed.

### Existing test coverage

| File | Tests | What they assert |
|---|---|---|
| `tests/test_mfa.py` | 6 | blocked/passes/unlisted-role-noop/empty-set; `platform_admin` in required set |
| `tests/test_auth.py` | 2 | MFA raise for platform_admin fixture; no-op for 7 existing roles |
| `tests/test_clerk_jwks.py` | 2 | claim → `mfa_verified` mapping |

**MFA enforcement is correct, fail-closed, and fully tested.** Inert only because `platform_admin` absent from role model.

---

## 4. Resolved owner decision

**Decision (2026-06-28):** `platform_admin` = **tenant-scoped role, Option A**.

Canonical wording (recorded in AUTH_AND_RBAC §4 and LAUNCH_BLOCKERS §2):

> `platform_admin` is stored in the existing tenant-scoped membership model for MVP, but its permissions are limited to explicit platform/admin routes and do not grant implicit tenant data access, RLS bypass, or tenant-owner powers.

### Permission boundary

| Capability | platform_admin |
|---|---|
| Platform routes (`/api/v1/platform/*`) | Yes |
| Platform health/ops read | Yes |
| Support-grant oversight | Yes |
| Tenant data read (without active support grant) | **No** |
| RLS bypass | **No** |
| Tenant membership/ownership bypass | **No** |
| Implicit tenant owner/admin powers | **No** |

MFA: **mandatory** (owner-resolved in Clerk readiness decision #4, LAUNCH_BLOCKERS §2).

Cross-tenant operations still require an active time-boxed support grant via `SupportAccessService`.

### Why Option A (not a global model)

Activates the already-wired `enforce_mfa()` with zero enforcement code change — it keys off `principal.role`. A separate `users.is_platform_admin` model would require principal-resolution restructuring and new MFA enforcement paths — deferred complexity not needed for MVP. Principal resolution path is identical to tenant roles.

---

## 5. P3-3e implementation spec (next slice — requires explicit approval)

Code+migration slice. Not implemented here.

### 5a. Migration (new file `backend/migrations/versions/00NN_platform_admin_role.py`)

```sql
-- down
ALTER TABLE tenant_memberships DROP CONSTRAINT ck_tenant_memberships_role;

-- up
ALTER TABLE tenant_memberships ADD CONSTRAINT ck_tenant_memberships_role
CHECK (role IN ('owner','admin','marketer','reviewer','viewer','billing_admin','support','platform_admin'));
```

Recommendation: add `'support'` in the same migration to reconcile the 3-source drift. Confirm with owner before cutting migration.

### 5b. `backend/app/services/authz.py`

Add to `ROLE_PERMISSIONS` (after line 83):
```python
"platform_admin": frozenset({
    # Explicit platform/ops permissions only — enumerated before P3-3e lands
    # Proposal: CAN_READ_PLATFORM_HEALTH, CAN_MANAGE_SUPPORT_GRANTS
    # (exact Permission constants to be defined in the code slice)
}),
```

Exact `Permission` constants to be defined and approved in the P3-3e plan before implementation.

### 5c. `backend/app/models/membership.py:21`

Add `"platform_admin"` (and `"support"`) to `ROLES` tuple.

### 5d. No enforcement code changes

`mfa.py`, `dependencies.py`, `config.py` require zero modification. MFA activates automatically.

### 5e. Production-only config (not committed)

Clerk JWT template must emit an MFA boolean claim (e.g. `"mfa": true`). Set `auth_provider_mfa_claim` via Secrets Manager/env. Not committed — deferred to production cutover.

---

## 6. Tests needed (P3-3e)

| Test | Assertion |
|---|---|
| `test_authz.py` — `platform_admin` permissions | Exact permission set asserted; no tenant-data permissions; default-deny for unlisted permissions |
| `test_authz.py` — no cross-tenant powers | `platform_admin` cannot impersonate owner/admin; IDOR checks still enforced |
| `test_auth.py` — MFA enforce (live role) | 403 `MFA_REQUIRED` when `platform_admin` + `mfa_verified=False`; passes when `True`; 7 existing roles unchanged (no-op) |
| Constraint round-trip | `platform_admin` (and `support`) insertable; unknown role rejected by CHECK constraint |
| RLS/isolation regression | `platform_admin` in tenant A cannot read tenant B data without active support grant |

---

## 7. Stop-gates

- **Migration mandatory** — no `platform_admin` row insertable without constraint change. P3-3e is not a no-op; explicit approval required (CLAUDE.md hard stop for code/migration changes).
- **Production cutover still blocked** (unchanged): real Clerk Production secrets from AWS Secrets Manager; frontend `@clerk/nextjs` wiring (deferred); real-JWT smoke; `auth_provider_mfa_claim` configured in prod. None in scope here.
- Do NOT enable production, add real Clerk secrets, weaken tenant RBAC/RLS/membership, bypass `current_principal` or membership checks, make routes public, start frontend Clerk, or start P3-4/P3-5/P3-6 / providers / sending / Stripe / SMS / live scraping.
- `support` role drift: flagged and documented, not fixed here.

---

## 8. Verification (this docs-only slice)

- `git status`: clean except 4 doc files (AUTH_AND_RBAC, LAUNCH_BLOCKERS, DOCUMENTATION_MANIFEST, this evidence doc).
- `grep -r 'platform_admin' backend/` — unchanged from `e62e55c` (exists in mfa.py, config.py, test fixtures; no new code).
- No change under `backend/` (code/migrations/tests) or `frontend/`.
- Cross-references: AUTH_AND_RBAC §4 ↔ LAUNCH_BLOCKERS §2/§6/§7 ↔ this doc ↔ DOCUMENTATION_MANIFEST all resolve.
- LAUNCH_BLOCKERS §7 `platform_admin` row = Resolved.
- LAUNCH_BLOCKERS §2 new row = Option A decision recorded.

---

## 9. Honest limits

- No code written; enforcement still inert until P3-3e ships.
- Exact `Permission` constants for `platform_admin` not yet enumerated — deferred to P3-3e plan.
- `support` drift not fixed — flagged only.
- MFA claim name not configured — requires Clerk JWT template setup (prod cutover, not P3-3e).
- Frontend Clerk integration not started — deferred.
