# P3-3e — platform_admin Role Implementation & MFA Enforcement

**Purpose:** Evidence for the P3-3e code slice implementing the `platform_admin` role decision from P3-3d.
**Status:** Complete.
**Related docs:** [AUTH_AND_RBAC](../AUTH_AND_RBAC.md) §4 · [LAUNCH_BLOCKERS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) §2/§6/§7 · [phase-3-3d-platform-admin-rbac-plan.md](phase-3-3d-platform-admin-rbac-plan.md)

---

## 1. Git state

- Branch: `master`
- HEAD at slice start: `d3982ac` (P3-3d docs-only)
- Committed as: see commit below after gates

---

## 2. Files changed

| File | Change |
|---|---|
| `backend/app/services/authz.py` | Added `CAN_ACCESS_PLATFORM = "platform:access"` constant; added `"platform_admin": frozenset({CAN_ACCESS_PLATFORM})` to `ROLE_PERMISSIONS` |
| `backend/app/models/membership.py:21` | Added `"platform_admin"` to `ROLES` tuple; `_ROLE_LIST` regenerates ORM `ck_tenant_memberships_role` CheckConstraint automatically |
| `backend/migrations/versions/00022_platform_admin_role.py` | New migration; `down_revision = "00021_outcomes"` |
| `backend/tests/test_authz.py` | Added `CAN_ACCESS_PLATFORM` + `ROLE_PERMISSIONS` imports; added `("platform_admin", set())` parametrize row; added `test_platform_admin_has_only_platform_access_permission`; added `test_platform_admin_cannot_grant_support_access_or_bypass_require_active`; added `test_platform_admin_role_migration_shape`; added `test_platform_admin_role_migration_offline_sql` |
| `backend/tests/test_auth.py` | Updated MFA test docstring (no longer "no-op in live code"); added `test_current_principal_platform_admin_with_mfa_passes` |

---

## 3. Migration

- **Revision:** `00022_platform_admin_role`
- **Down-revision:** `00021_outcomes` (true alembic head confirmed by glob)
- **Upgrade:** drops + recreates `ck_tenant_memberships_role` with 7 roles (original 6 + `platform_admin`)
- **Downgrade:** drops + recreates with original 6-role list
- **Scope:** role CHECK constraint only — does NOT touch RLS, policies, other tables
- **Offline SQL verified:** `platform_admin` in generated SQL, constraint name correct, no RLS keywords

---

## 4. Final role list (DB constraint after 00022)

```
owner, admin, marketer, reviewer, viewer, billing_admin, platform_admin
```

ORM `ROLES` tuple matches. `test_tenancy_schema.py:46` auto-validates on every test run.

---

## 5. platform_admin permission set

```python
"platform_admin": frozenset({"platform:access"})
```

`CAN_ACCESS_PLATFORM = "platform:access"` — new platform-namespace constant, isolated from the 15 existing tenant-namespace constants. No existing role receives this permission; no cross-contamination.

**What platform_admin CANNOT do (enforced by RBAC default-deny):**
- No `CAN_READ_DASHBOARD`, `CAN_IMPORT_CONTACTS`, `CAN_CREATE_CAMPAIGN`, `CAN_RUN_CAMPAIGN`, `CAN_REVIEW_DRAFT`, `CAN_APPROVE_DRAFT`, `CAN_SCHEDULE_SEND` — no tenant data access
- No `CAN_MANAGE_TEAM`, `CAN_MANAGE_BILLING`, `CAN_READ_AUDIT`, `CAN_MANAGE_INTEGRATIONS` — no tenant-admin powers
- No `CAN_GRANT_SUPPORT_ACCESS` — cannot issue support grants
- No `CAN_USE_SUPPORT_ACCESS` — cannot bypass `require_active` (still denied without an active grant)

---

## 6. Support role drift — decision to defer

`support` was intentionally kept out of `tenant_memberships.role` and `ROLES`. `membership.py` comment: "by design (cross-tenant)". Support access is grant-based (`SupportAccessService`, 60-min TTL, audited) — making `support` an insertable membership role would create a persistent non-grant path to `CAN_USE_SUPPORT_ACCESS`, weakening the support-access model. Deferred per task constraint ("reconcile only if tests prove safe"). Documented here; `ROLE_PERMISSIONS["support"]` vestigial entry remains.

---

## 7. MFA enforcement result

`enforce_mfa()` (`backend/app/auth/mfa.py:27-37`) wired at `auth/dependencies.py:75` — **now enforced in live flow** for `platform_admin` principals:
- `platform_admin` + `mfa_verified=False` → `AppError("MFA_REQUIRED", 403)` ✓
- `platform_admin` + `mfa_verified=True` → passes ✓
- 7 existing roles (owner/admin/marketer/reviewer/viewer/billing_admin/support) remain no-op ✓

No code change to `mfa.py`, `dependencies.py`, or `config.py` — activation was automatic by adding the role.

**Production MFA claim still not configured** (intentional — deferred to production cutover):
- `auth_provider_mfa_claim = None` (default) → `mfa_verified` always `False` in live Clerk flow
- Real Clerk JWT template must emit a boolean MFA claim; `auth_provider_mfa_claim` set via Secrets Manager/env at cutover

---

## 8. Tests added/updated

| Test | File | Status |
|---|---|---|
| `test_role_permission_matrix_and_default_deny[platform_admin-*]` | test_authz.py | New parametrize row — asserts no tenant perm granted |
| `test_platform_admin_has_only_platform_access_permission` | test_authz.py | New — asserts `CAN_ACCESS_PLATFORM` True, all tenant perms False, owner does NOT get platform perm |
| `test_platform_admin_cannot_grant_support_access_or_bypass_require_active` | test_authz.py | New — FORBIDDEN on grant attempt, SUPPORT_ACCESS_DENIED on require_active without grant |
| `test_platform_admin_role_migration_shape` | test_authz.py | New — source-text assertions on migration 00022 |
| `test_platform_admin_role_migration_offline_sql` | test_authz.py | New — offline alembic SQL confirms `platform_admin` in constraint, no RLS |
| `test_current_principal_enforces_mfa_for_platform_admin_role` | test_auth.py | Updated docstring (no longer "currently no-op") |
| `test_current_principal_platform_admin_with_mfa_passes` | test_auth.py | New — `mfa_verified=True` passes gate |

---

## 9. Gate results

| Gate | Result |
|---|---|
| `ruff check app tests` | ✓ PASS |
| `black --check app tests` | ✓ PASS |
| `mypy app --ignore-missing-imports` | ✓ PASS (148 source files) |
| `pytest` | ✓ **576 passed** (was 570 — 6 new tests) |
| Frontend lint | ✓ No ESLint warnings or errors |
| Frontend typecheck | ✓ PASS |
| Frontend test | ✓ 122 passed |
| Frontend build | ✓ PASS |
| Offline alembic SQL (00021→00022) | ✓ `platform_admin` in SQL, constraint name correct, no RLS |
| Safety grep (secrets/prod-cutover) | ✓ No hits |

---

## 10. Remaining production auth blockers (unchanged)

| Blocker | Status |
|---|---|
| Real Clerk Production project provisioned | Not done — owner action required |
| `AUTH_PROVIDER_ISSUER` / JWKS / secret sourced from AWS Secrets Manager | Not done — requires real Clerk project |
| `auth_provider_mfa_claim` configured in prod (Clerk JWT template emits MFA boolean) | Not done — deferred to cutover |
| Frontend `@clerk/nextjs` `ClerkProvider` + `getToken()` wired | Not done — deferred |
| Real-JWT end-to-end smoke with real Clerk | Not done — requires real Clerk project |
| Live DB migration (alembic upgrade head on prod/staging) | Not done — no production target |

---

## 11. Honest limits

- No production enable, no real Clerk secrets, no `.env` edits, no frontend Clerk, no public routes.
- No RLS/tenant isolation regression — platform_admin is tenant-scoped, loads from `tenant_memberships`, no implicit cross-tenant access.
- `support` drift deferred (documented in §6 above).
- `platform:access` is a placeholder permission — actual platform route gating (`/api/v1/platform/*`) requires P3-4+ route implementation that calls `rbac.require(principal, CAN_ACCESS_PLATFORM)`.
- MFA inert in production until `auth_provider_mfa_claim` configured and Clerk JWT template emits the claim.
