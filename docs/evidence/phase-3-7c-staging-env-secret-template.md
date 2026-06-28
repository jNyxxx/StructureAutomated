# P3-7c — Staging Environment and Secret Template Docs

**Purpose:** Create a safe staging environment/config map and secret-reference template before any staging release work.
**Status:** Docs-only template complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `08fd608 docs(p3-7): verify production Docker image builds`

---

## 1. Scope and hard stop

P3-7c is documentation only.

Confirmed not done:

- no cloud provisioning;
- no image registry push;
- no staging or production release;
- no real `.env` file edit;
- no application/config/migration/Dockerfile/package change;
- no real secrets added;
- no Resend adapter, SDK, API call, or live email delivery;
- no Stripe, SMS, or live scraping;
- no boot-guard weakening;
- no auth/RBAC/RLS/tenant-isolation change;
- no billing or send-gate bypass.

---

## 2. Files created / updated

Created:

- `docs/STAGING_ENVIRONMENT_TEMPLATE.md`
- `docs/evidence/phase-3-7c-staging-env-secret-template.md`

Updated:

- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

---

## 3. Staging environment template summary

`docs/STAGING_ENVIRONMENT_TEMPLATE.md` defines a safe staging config map grouped by:

- backend API;
- frontend;
- worker;
- migration task;
- database/RDS;
- Redis/rate limit;
- Clerk managed auth;
- mock billing / Stripe disabled state;
- Resend disabled state;
- observability/logging.

The template keeps staging production-like for infrastructure proof while preserving the required stop gates:

- `APP_ENV=staging`, not production;
- production Docker images are allowed;
- managed Postgres/RDS is expected;
- managed Redis is expected;
- real Clerk staging smoke is allowed only when Clerk values exist;
- billing stays mock;
- sending stays mock/disabled;
- Stripe/SMS/live scraping stay disabled.

---

## 4. Secret refs / naming summary

Recommended convention:

```text
/automatedstructure/staging/<service>/<NAME>
```

Required example refs:

```text
/automatedstructure/staging/backend/DATABASE_URL
/automatedstructure/staging/backend/DATABASE_DSN
/automatedstructure/staging/backend/JWT_SECRET
/automatedstructure/staging/backend/ENCRYPTION_KEY
/automatedstructure/staging/backend/WEBHOOK_SECRET
/automatedstructure/staging/redis/RATE_LIMIT_REDIS_URL
/automatedstructure/staging/clerk/ISSUER
/automatedstructure/staging/clerk/JWKS_URL
/automatedstructure/staging/clerk/AUDIENCE
/automatedstructure/staging/clerk/AZP
/automatedstructure/staging/clerk/MFA_CLAIM
/automatedstructure/staging/clerk/PUBLISHABLE_KEY
/automatedstructure/staging/clerk/SECRET_KEY
/automatedstructure/staging/email/RESEND_API_KEY
/automatedstructure/staging/email/RESEND_WEBHOOK_SECRET
/automatedstructure/staging/kms/KEY_ALIAS
```

Resend secret refs are documented as placeholder naming only until P3-5f+ gates clear. The default staging config remains:

```text
EMAIL_PROVIDER=mock
LIVE_EMAIL_SENDING_ENABLED=false
```

No raw secrets are included.

---

## 5. Boot-guard staging requirements

Current code-level boot guard fails closed only when `APP_ENV=production`. P3-7c therefore defines a staging release preflight/smoke policy without changing application behavior.

Staging must prove:

- secret-backed values are not placeholder-like;
- `SECRET_BACKEND` points to AWS Secrets Manager or an approved staging equivalent;
- `KMS_KEY_ID` / alias / path is present;
- `RATE_LIMIT_BACKEND=redis`;
- Redis URL is secret-backed and managed;
- runtime DB role is not SUPERUSER and does not have BYPASSRLS;
- migrations are run before backend readiness acceptance;
- `/ready` reports database ok, migrations up_to_date, and redis ok;
- Clerk config is present when managed-auth smoke is in scope;
- live email delivery remains disabled unless full Resend gates clear separately;
- Stripe/SMS/live scraping remain disabled unless separately approved;
- CORS is allowlisted, not open;
- HTTPS/cookie/CSRF settings are production-like for staging domains.

If any item fails, staging release must stop.

---

## 6. Allowed / disallowed matrix

Allowed in staging:

- managed auth smoke if Clerk staging values exist;
- mock billing;
- mock/disabled sending;
- production Docker images;
- RDS/managed Postgres;
- managed Redis;
- migrations;
- health/live/ready checks;
- synthetic demo data.

Disallowed in staging by default:

- prospect/client real email delivery;
- Stripe money movement;
- SMS;
- live scraping;
- production domain cutover;
- public launch;
- real customer data unless separately approved.

---

## 7. Staging smoke checklist

Minimum staging smoke checklist defined:

1. Run migrations.
2. Boot backend.
3. `/health` returns 200.
4. `/live` returns 200.
5. `/ready` returns database ok, migrations up_to_date, redis ok.
6. Boot frontend.
7. Frontend calls backend API URL.
8. Clerk staging login works if values exist.
9. Tenant/RLS smoke passes.
10. Rate-limit Redis smoke returns expected 429 behavior.
11. Controlled Redis-down test returns sanitized 503 behavior.
12. Mock billing gate smoke passes.
13. Send-gate dry-run smoke passes only in mock/no-send mode.
14. Confirm no real send occurred.
15. Audit event smoke passes.
16. Worker smoke only after approved worker command exists.
17. Logs checked for DSN/Redis/JWT/Clerk/provider secret leakage.
18. Rollback path identified before release signoff.

---

## 8. Remaining owner / operator values

Still missing before any staging release work:

- AWS account ID;
- AWS region;
- deployment platform confirmation;
- staging frontend domain;
- staging API domain;
- DNS/TLS owner;
- Secrets Manager owner;
- KMS key owner / alias;
- RDS owner and sizing;
- Redis owner and sizing;
- backup retention;
- RPO/RTO;
- alert recipients;
- CI/CD approver;
- migration approver;
- rollback approver;
- production cutover approver;
- Clerk staging values;
- confirmation that Resend stays disabled until P3-5f+ gates clear.

---

## 9. Final verdict

P3-7c is complete as a docs-only staging environment and secret-reference template.

The future staging release remains blocked until the owner/operator values above are supplied and a later P3-7 slice is explicitly approved.
