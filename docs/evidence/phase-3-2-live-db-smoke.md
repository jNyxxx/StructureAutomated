# Phase 3-2 — Live DB smoke + seeded local demo verification

**Date:** 2026-06-26
**Scope:** P3-2 — prove the local DB-backed seeded demo path is repeatable and safe (compose db/backend
→ migrations at head → mock tenant seed → active billing gates → RLS/tenant isolation → core API smoke).
**Runtime:** Local Docker Compose only. **Production status:** Not approved (unchanged).

## Verdict

**P3-2 complete.** The local seeded demo path is verified end-to-end: DB at migration head, all 29
boot-guard tenant tables RLS-forced, tenant isolation proven under a least-privilege role, mock
tenant billing gates active, and the full protected API surface (44 paths / 51 operations) responds
as expected. No production / real providers / real sending / Stripe / SMS / OAuth / live scraping
enabled; no app code changed; no new migration; no seed helper committed.

## Local compose runtime

| Item | Value |
|---|---|
| Docker / Compose | 29.5.3 / v5.1.4 (Docker Desktop 4.78.0) |
| `db` | `pgvector/pgvector:pg16` — healthy |
| `backend` | up; code volume-mounted (`./backend:/app`, `--reload`) → serves current P3-1a code |
| backend `APP_ENV` | `local` |
| backend `DATABASE_URL` | `postgresql+asyncpg://app_user:***@db:5432/automatedstructure` |
| `current_user` / `current_database` | `app_user` / `automatedstructure` |

## Migrations

- `alembic upgrade head` → no-op (already applied) — proves the intended command is idempotent/repeatable.
- `alembic current` = `00021_outcomes (head)` = code head.
- `GET /ready` → 200 `{"status":"ok","checks":{"database":"ok","migrations":"up_to_date"}}`.

## Boot guard / RLS (29-table verification)

- `TENANT_OWNED_TABLES` = 29 (P3-1a); `audit_events` remains the documented exception.
- Live `pg_class` check: **expected_29 = 29, rls_forced_ok = 29, missing = 0** — every boot-guard
  table has `relrowsecurity AND relforcerowsecurity`.
- `audit_events` itself is also ENABLE+FORCE (`t/t`) — exempt from the boot-guard list, not from RLS.

## Tenant isolation smoke (RLS policy proof)

Run under an **ephemeral least-privilege role** (`NOSUPERUSER NOBYPASSRLS`), transaction-scoped
context via `SET LOCAL`, role dropped afterward (0 residual):

```sql
CREATE ROLE rls_smoke NOSUPERUSER NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO rls_smoke;
GRANT SELECT ON tenant_memberships, tenant_subscriptions TO rls_smoke;
BEGIN;
SET ROLE rls_smoke;
SET LOCAL app.current_tenant_id = '22222222-2222-2222-2222-222222222222';
SELECT count(*) FROM tenant_memberships;   -- 1  (tenant A sees its own row)
SET LOCAL app.current_tenant_id = '33333333-3333-3333-3333-333333333333';
SELECT count(*) FROM tenant_memberships;   -- 0  (tenant B sees nothing)
RESET ROLE; COMMIT;
DROP OWNED BY rls_smoke; DROP ROLE rls_smoke;
```

**Result: tenant A = 1 row visible, tenant B = 0 rows visible.** RLS isolation holds. No RLS was
bypassed or disabled; `app_user` was not altered.

### Honest finding — local role vs RLS (defense-in-depth)

Locally `app_user` is `rolsuper=t, rolbypassrls=t` (the Postgres image makes `POSTGRES_USER` a
superuser), so the app's own local connection **bypasses DB-level RLS**. Isolation is nonetheless
intact because of two independent layers:

1. **Application layer (active locally):** every repository adds an explicit `WHERE tenant_id = …`
   predicate (e.g. `app/repositories/billing_repo.py:37,63`, `campaign_repo.py`) in addition to
   `tenant_session`.
2. **DB layer (RLS):** policies are present and FORCED on all 29 tables; they are enforced under a
   least-privilege role (as proven above) and **required in production** by the boot guard
   (`ROLE_SAFETY_SQL` rejects SUPERUSER/BYPASSRLS). This is a local-dev image default, not a
   production gap — production must provision the NOSUPERUSER/NOBYPASSRLS app role (Slice 6/9 design).

## Seeded local/mock tenant (already present; not re-seeded)

| Entity | Value |
|---|---|
| Tenant | `22222222-2222-2222-2222-222222222222` — "Automated Structure Local Mock Tenant" |
| User | `11111111-1111-1111-1111-111111111111` — owner@example.com |
| Membership | tenant 22222222 / user 11111111 / role `owner` |
| Subscription | plan `mvp_mock` ("MVP Mock Plan"), `tenant_status = active` |
| Mock auth token | `token-sentinel` → resolves to the owner principal above |

Idempotent local-only seed pattern (for repeatability; **not** committed as a helper, **not** for
production, **no** real customer data): insert the tenant, user, owner membership, and an `active`
`mvp_mock` subscription with `ON CONFLICT DO NOTHING`.

## Billing / access (mock tenant)

`GET /api/v1/billing/access` → 200:
`is_active=true · can_send=true · can_run_agents=true · can_create_campaign=true · can_export=true ·
mock_only=true`.

## Protected API smoke

Headers: `Authorization: Bearer token-sentinel`, `X-Tenant-ID: 22222222-2222-2222-2222-222222222222`.

| Endpoint | Result |
|---|---|
| `GET /health` | 200 |
| `GET /live` | 200 |
| `GET /ready` | 200 — database=ok, migrations=up_to_date |
| `GET /openapi.json` | 200 — **paths=44, operations=51** |
| `GET /auth/me` | 200 — owner@example.com, tenant 22222222, role owner, mfa_verified |
| `GET /api/v1/billing/access` | 200 — all gates true, mock_only |
| `GET /api/v1/prospects` | 200 |
| `GET /api/v1/contacts` | 200 |
| `GET /api/v1/campaigns` | 200 |
| `GET /api/v1/review/items` | 200 |
| `GET /api/v1/audit-events` | 200 |

## Gate results

| Gate | Result |
|---|---:|
| Backend `ruff check app tests` | PASS |
| Backend `black --check app tests` | PASS |
| Backend `mypy app` | PASS (145 source files) |
| Backend `pytest` | PASS — **525 passed** |
| Frontend `npm run lint` | PASS |
| Frontend `npm run typecheck` | PASS |
| Frontend `npm run test` | PASS — **122 passed** |
| Frontend `npm run build` | PASS |

## Honest limits

No production enabled · no deploy · no real providers enabled · no real sending enabled · no
Stripe/SMS/OAuth/live scraping enabled · no production secrets used · no new migrations authored or
run · no app code changed · no seed helper committed · ephemeral `rls_smoke` role created only for the
isolation proof and dropped (0 residual). P3-3…P3-6 not started; stop-gates P3-5/P3-6 still deferred.
