# Staging Environment Template

**Purpose:** Safe staging configuration map for AutomatedStructure before any cloud release work.
**Status:** Template only. No real secrets, no cloud resources, no public launch.
**Last updated:** 2026-06-28 (Asia/Manila)

---

## 1. Hard stop

This template is not a runnable secrets file.

Do not paste raw secrets into this document, Git, logs, tickets, screenshots, prompts, audit rows, frontend config, or client responses.

Staging must keep these disabled unless a later owner-approved slice explicitly changes the scope:

- Resend/live email delivery;
- Stripe money movement;
- SMS;
- live scraping;
- public launch / production cutover;
- real customer data loading.

---

## 2. Secret reference convention

Use AWS Secrets Manager paths or the owner-approved equivalent. Config should reference paths/aliases; runtime secret injection should resolve values outside Git.

Recommended path pattern:

```text
/automatedstructure/staging/<service>/<NAME>
```

Required path examples:

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

Resend secret paths are placeholders only until P3-5f+ gates clear. Keep `EMAIL_PROVIDER=mock` and `LIVE_EMAIL_SENDING_ENABLED=false` for the default staging environment.

---

## 3. Backend API environment map

| Variable | Staging value / source | Required? | Notes |
|---|---|---:|---|
| `APP_ENV` | `staging` | Yes | Do not use `production` for staging. |
| `SERVICE_NAME` | `backend` | Yes | Used for logs/metrics grouping. |
| `LOG_LEVEL` | `INFO` | Yes | Avoid debug logs unless short-lived and approved. |
| `DATABASE_URL` | secret ref: `/automatedstructure/staging/backend/DATABASE_URL` | Yes | Async SQLAlchemy app DSN. Must use app runtime DB role. |
| `JWT_SECRET` | secret ref: `/automatedstructure/staging/backend/JWT_SECRET` | Yes | No placeholder values. |
| `ENCRYPTION_KEY` | secret ref: `/automatedstructure/staging/backend/ENCRYPTION_KEY` | Yes | No placeholder values. |
| `WEBHOOK_SECRET` | secret ref: `/automatedstructure/staging/backend/WEBHOOK_SECRET` | Yes | Generic app webhook secret; provider webhooks separate. |
| `SECRET_BACKEND` | `aws` or staging-approved equivalent | Yes | Use secret backend, not committed files. |
| `KMS_KEY_ID` | secret/config ref: `/automatedstructure/staging/kms/KEY_ALIAS` | Yes | Owner-approved KMS key alias/path. |
| `COOKIE_SECURE` | `true` | Yes | Required for TLS staging domains. |
| `CSRF_ENABLED` | `true` | Yes | Required for browser flows. |
| `HTTPS_ONLY` | `true` | Yes | Staging must be HTTPS. |
| `CORS_ALLOW_ALL` | `false` | Yes | Allowlist staging frontend domain only. |
| `RATE_LIMIT_ENABLED` | `true` | Yes | Baseline middleware + endpoint limits. |
| `RATE_LIMIT_BACKEND` | `redis` | Yes | Required for multi-worker/staging parity. |
| `RATE_LIMIT_REDIS_URL` | secret ref: `/automatedstructure/staging/redis/RATE_LIMIT_REDIS_URL` | Yes | Must be managed Redis/ElastiCache URL. |
| `AUTH_PROVIDER` | `managed` | Yes | Clerk managed auth path. |
| `MOCK_VERIFIER` | `false` when Clerk staging values exist | Yes for managed-auth smoke | If Clerk values are unavailable, staging cannot complete real-auth smoke. |
| `MOCK_STRIPE` | `true` | Yes | Billing remains mock. |
| `MOCK_MAILBOX` | `true` | Yes | Mailbox remains mock. |
| `MOCK_DNS` | `true` | Yes | DNS checks remain mock unless separate DNS slice approves real check. |
| `MOCK_RESEARCH` | `true` unless approved otherwise | Yes | Keep deterministic/safe staging behavior. |
| `EMAIL_PROVIDER` | `mock` | Yes | Resend adapter is not active. |
| `LIVE_EMAIL_SENDING_ENABLED` | `false` | Yes | Must stay false in default staging. |
| `EMAIL_PROVIDER_SECRET_REF` | placeholder path only: `/automatedstructure/staging/email/RESEND_API_KEY` | Optional placeholder | Do not resolve until P3-5f+ gates clear. |
| `EMAIL_PROVIDER_WEBHOOK_SECRET_REF` | placeholder path only: `/automatedstructure/staging/email/RESEND_WEBHOOK_SECRET` | Optional placeholder | Do not resolve until P3-5f+ gates clear. |
| `EMAIL_SENDING_DOMAIN` | `outreach.automatedstructure.com` once DNS proof exists | Not for default staging | Do not enable delivery from it yet. |

---

## 4. Frontend environment map

| Variable | Staging value / source | Required? | Notes |
|---|---|---:|---|
| `NODE_ENV` | `production` inside image | Yes | Set by `frontend/Dockerfile.prod`. |
| `NEXT_PUBLIC_API_BASE_URL` | `https://api-staging.automatedstructure.com` or owner-approved API URL | Yes | Must point to staging backend only. |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | secret/config ref: `/automatedstructure/staging/clerk/PUBLISHABLE_KEY` | Required for Clerk staging smoke | Public key, but still sourced through approved config. |
| `NEXT_PUBLIC_APP_ENV` | `staging` | Optional | Public label only. |
| `NEXT_TELEMETRY_DISABLED` | `1` | Yes | Set in Dockerfile; may also be set at runtime. |

Do not expose backend secrets, Clerk secret key, DB URLs, Redis URLs, provider credentials, webhook secrets, or KMS refs to the browser.

---

## 5. Worker environment map

The future staging worker should reuse the backend production image with an approved worker command override after the worker entrypoint is finalized.

| Variable | Staging value / source | Required? | Notes |
|---|---|---:|---|
| `APP_ENV` | `staging` | Yes | Same environment policy as backend. |
| `SERVICE_NAME` | `worker` | Yes | Separate logs/metrics stream. |
| `DATABASE_URL` | secret ref: `/automatedstructure/staging/backend/DATABASE_URL` | Yes | Same app role, no superuser/BYPASSRLS. |
| `SECRET_BACKEND` | `aws` or staging-approved equivalent | Yes | No committed secrets. |
| `KMS_KEY_ID` | secret/config ref: `/automatedstructure/staging/kms/KEY_ALIAS` | Yes | Same KMS policy. |
| `RATE_LIMIT_BACKEND` | `redis` | Yes | Required for parity if worker uses limiter utilities. |
| `RATE_LIMIT_REDIS_URL` | secret ref: `/automatedstructure/staging/redis/RATE_LIMIT_REDIS_URL` | Yes | Managed Redis. |
| `EMAIL_PROVIDER` | `mock` | Yes | No Resend send worker. |
| `LIVE_EMAIL_SENDING_ENABLED` | `false` | Yes | No live send worker. |
| `MOCK_STRIPE` / `MOCK_MAILBOX` / `MOCK_DNS` / `MOCK_RESEARCH` | `true` unless separately approved | Yes | Preserve mock provider boundaries. |

Worker command remains blocked until an approved worker entrypoint/command exists.

---

## 6. Migration task environment map

Use a one-off task with the backend production image and an approved migration command.

| Variable | Staging value / source | Required? | Notes |
|---|---|---:|---|
| `APP_ENV` | `staging` | Yes | Not production. |
| `SERVICE_NAME` | `migration` | Yes | Separate logs. |
| `DATABASE_URL` or migration DSN | secret ref: `/automatedstructure/staging/backend/DATABASE_URL` or dedicated migration role ref | Yes | Prefer least privilege; migration role must be approved. |
| `SECRET_BACKEND` | `aws` or staging-approved equivalent | Yes | Required if task loads secrets. |
| `KMS_KEY_ID` | secret/config ref: `/automatedstructure/staging/kms/KEY_ALIAS` | Yes | Required if task resolves secrets. |

Migration smoke must run before backend readiness is accepted. `/ready` must report migrations as `up_to_date`.

---

## 7. Database / RDS requirements

Required staging DB properties:

- PostgreSQL 16-compatible target with required extensions from migrations;
- app runtime role is not SUPERUSER;
- app runtime role does not have BYPASSRLS;
- migrations applied before app readiness acceptance;
- forced RLS remains enabled on tenant-owned tables;
- backups enabled with owner-approved retention;
- restore drill planned before production cutover;
- DSNs stored only as secret refs.

Recommended secret refs:

```text
/automatedstructure/staging/backend/DATABASE_URL
/automatedstructure/staging/backend/DATABASE_DSN
```

Use `DATABASE_URL` for the app/runtime async SQLAlchemy URL. Use `DATABASE_DSN` only if a tool/task explicitly requires the non-SQLAlchemy form.

---

## 8. Redis / rate-limit requirements

Required staging Redis properties:

- managed Redis/ElastiCache or owner-approved managed equivalent;
- `RATE_LIMIT_BACKEND=redis`;
- `RATE_LIMIT_REDIS_URL` from secret ref only;
- `/ready` must show `redis=ok`;
- Redis-down smoke must fail closed with `503 RATE_LIMIT_BACKEND_UNAVAILABLE` in a controlled staging test.

Recommended secret ref:

```text
/automatedstructure/staging/redis/RATE_LIMIT_REDIS_URL
```

---

## 9. Clerk staging requirements

Required refs/config:

```text
/automatedstructure/staging/clerk/ISSUER
/automatedstructure/staging/clerk/JWKS_URL
/automatedstructure/staging/clerk/AUDIENCE
/automatedstructure/staging/clerk/AZP
/automatedstructure/staging/clerk/MFA_CLAIM
/automatedstructure/staging/clerk/PUBLISHABLE_KEY
/automatedstructure/staging/clerk/SECRET_KEY
```

Backend env mapping:

```text
AUTH_PROVIDER=managed
AUTH_PROVIDER_ISSUER=<resolved from ISSUER>
AUTH_PROVIDER_JWKS_URL=<resolved from JWKS_URL or blank to derive from issuer>
AUTH_PROVIDER_AUDIENCE=<resolved from AUDIENCE if configured>
AUTH_PROVIDER_AUTHORIZED_PARTIES=<resolved from AZP if configured>
AUTH_PROVIDER_MFA_CLAIM=<resolved from MFA_CLAIM>
AUTH_PROVIDER_PUBLISHABLE_KEY=<resolved from PUBLISHABLE_KEY>
AUTH_PROVIDER_SECRET_KEY=<resolved from SECRET_KEY>
AUTH_MFA_REQUIRED_ROLES=platform_admin
```

Frontend env mapping:

```text
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<resolved public staging key>
```

Staging cannot pass managed-auth smoke until Clerk staging values exist.

---

## 10. Billing / Stripe status

Default staging state:

```text
MOCK_STRIPE=true
```

Allowed:

- mock billing states;
- centralized access gate smoke;
- tenant/subscription/plan relationship smoke;
- billing UI smoke against mock/local API.

Disallowed:

- Stripe checkout;
- Stripe webhooks;
- Stripe money movement;
- real subscription/customer sync.

---

## 11. Resend / email status

Default staging state:

```text
EMAIL_PROVIDER=mock
LIVE_EMAIL_SENDING_ENABLED=false
EMAIL_PROVIDER_SECRET_REF=/automatedstructure/staging/email/RESEND_API_KEY
EMAIL_PROVIDER_WEBHOOK_SECRET_REF=/automatedstructure/staging/email/RESEND_WEBHOOK_SECRET
EMAIL_SENDING_DOMAIN=outreach.automatedstructure.com
```

The Resend refs above are naming placeholders only. Do not resolve or inject real Resend values until P3-5f+ gates clear.

Allowed:

- send-gate dry-run;
- mock send-intent smoke;
- suppression/compliance/review gate smoke;
- webhook design/docs work;
- internal-only Resend smoke preparation docs.

Disallowed by default:

- prospect/client real email delivery;
- Resend API calls;
- Resend webhook endpoint exposure with real secret;
- internal-only real smoke until P3-5h concrete values and approval are recorded;
- open/click tracking.

---

## 12. Observability / logging environment map

| Variable | Staging value / source | Required? | Notes |
|---|---|---:|---|
| `LOG_LEVEL` | `INFO` | Yes | Use structured logs; avoid debug by default. |
| `SERVICE_NAME` | `backend` / `worker` / `migration` | Yes | Separate log streams. |
| `APP_ENV` | `staging` | Yes | Log environment labels. |
| `REQUEST_ID` / correlation middleware | app-generated | Yes | Do not trust client-supplied secrets. |
| Alert destination | owner-provided recipient/channel | Required before staging release | No secrets in alert payloads. |

Staging logs must be checked for:

- no DSN leakage;
- no Redis URL leakage;
- no JWT/session secret leakage;
- no Clerk secret leakage;
- no provider credential leakage;
- no raw webhook payload leakage;
- no PII in rate-limit keys/logs.

---

## 13. Boot-guard staging requirements

Current code-level boot guard fails closed only when `APP_ENV=production`. For staging, use this template as a required release preflight and smoke policy without changing `APP_ENV` to production.

Staging release must prove:

- placeholder-like secrets are not used for secret-backed values;
- `SECRET_BACKEND` points to AWS Secrets Manager or approved staging equivalent;
- `KMS_KEY_ID`/alias/path is present;
- `RATE_LIMIT_BACKEND=redis`;
- Redis URL is secret-backed and managed;
- DB role is not SUPERUSER and does not have BYPASSRLS;
- migrations run before backend readiness acceptance;
- `/ready` reports database ok, migrations up_to_date, and redis ok;
- Clerk config is present when managed-auth smoke is in scope;
- live sending remains disabled unless full Resend gates clear in a separate slice;
- Stripe/SMS/live scraping remain disabled unless separately approved;
- CORS is allowlisted, not open;
- HTTPS/cookie/CSRF settings are production-like for staging domains.

If any item fails, staging release must stop.

---

## 14. Staging allowed / disallowed matrix

| Capability | Allowed in staging? | Notes |
|---|---:|---|
| Managed auth smoke with Clerk staging values | Yes | Only after owner supplies Clerk values. |
| Mock billing | Yes | Money movement remains disabled. |
| Mock/disabled sending | Yes | Default and required. |
| Production Docker images | Yes | P3-7b images are build-green. |
| RDS/managed Postgres | Yes | Required for realistic staging. |
| Managed Redis | Yes | Required for rate-limit parity. |
| Migrations | Yes | Must run before readiness acceptance. |
| Health/live/ready checks | Yes | Required. |
| Synthetic demo data | Yes | Do not use real customer data without separate approval. |
| Prospect/client real email sending | No | Resend/live delivery remains off. |
| Stripe money movement | No | Deferred. |
| SMS | No | Deferred. |
| Live scraping | No | Deferred. |
| Production domain cutover | No | Separate go/no-go only. |
| Public launch | No | Separate approval only. |
| Real customer data | No by default | Requires separate privacy/security approval. |

---

## 15. Staging smoke checklist

Minimum checklist:

1. Run migrations in one-off task.
2. Boot backend service with staging config.
3. `/health` returns 200.
4. `/live` returns 200.
5. `/ready` returns database ok, migrations up_to_date, redis ok.
6. Boot frontend service from production image.
7. Frontend can call backend API URL.
8. Clerk staging login works if Clerk values exist.
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

## 16. Remaining owner / operator values

Still needed before staging release work:

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

## 17. Final verdict

This template is ready for owner/operator review.

It does not approve staging release. It only defines the safe staging config map, secret-ref naming convention, boot-preflight requirements, and smoke checklist for a later approved staging slice.
