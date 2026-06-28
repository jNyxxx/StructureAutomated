# P3-7d — CI/CD Release Pipeline Plan

**Purpose:** Define the staging and future production CI/CD release pipeline plan without implementing deployment automation.
**Status:** Docs-only plan complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `bd1f3ee docs(p3-7): add staging environment secret template`

---

## 1. Scope and hard stop

P3-7d is documentation only.

Confirmed not done:

- no GitHub Actions workflow implementation or edit;
- no deployment;
- no image registry push;
- no AWS provisioning;
- no production enablement;
- no real `.env` file edit;
- no real secrets added;
- no Resend adapter, SDK, API call, or live email delivery;
- no Stripe, SMS, or live scraping;
- no boot-guard weakening;
- no auth/RBAC/RLS/tenant-isolation change;
- no billing or send-gate bypass.

---

## 2. Current CI state

Existing workflow:

```text
.github/workflows/ci.yml
```

Current triggers:

```text
push to main/master
pull_request
```

Current backend coverage:

- Python 3.12 setup;
- editable install with `[dev]` extras;
- Ruff lint;
- Black format check;
- mypy type check;
- pytest;
- Postgres/pgvector service;
- Alembic migration smoke: upgrade head -> downgrade base -> upgrade head.

Current frontend coverage:

- Node 20 setup;
- install dependencies;
- lint;
- typecheck;
- Vitest test;
- Next build.

Current safety coverage:

- gitleaks secret scan;
- pre-commit hook job.

Current Docker coverage:

- no production backend Docker image build in CI yet;
- no production frontend Docker image build in CI yet;
- P3-7b-verify proved local production Docker builds manually.

Current deploy/promotion coverage:

- no staging deploy job;
- no production deploy job;
- no environment approval gates;
- no registry push;
- no migration one-off task automation;
- no smoke evidence upload;
- no rollback automation.

Planning note:

- `frontend/package-lock.json` is now committed and P3-7b-verify proved Docker `npm ci` needs it. Future CI implementation should switch frontend dependency install from `npm install` to `npm ci`, but P3-7d does not edit workflow files.

---

## 3. Proposed staging CI/CD pipeline

### 3.1 Trigger rules

Recommended staging pipeline triggers:

- pull request: validation only, no image push, no deploy;
- push to `master`: validation + build images, but deploy only after environment approval;
- manual `workflow_dispatch`: allowed for staging release retries and smoke-only reruns;
- tags/releases: not needed until production release convention is approved.

### 3.2 Branch protection expectations

Protect `master` with:

- required backend CI job;
- required frontend CI job;
- required secret scan;
- required pre-commit job;
- required production Docker build jobs once added;
- no direct push except approved maintainers;
- pull request review required;
- linear history or squash policy per owner decision;
- status checks must pass before merge.

### 3.3 Backend gates

Staging pipeline backend checks:

```text
python -m ruff check app tests
python -m black --check app tests
python -m mypy app --ignore-missing-imports
python -m pytest
alembic upgrade head / downgrade base / upgrade head smoke against Postgres+pgvector
```

Optional stronger release check:

- assert code Alembic head equals DB head after migration smoke;
- run boot-guard/config preflight against a staging-shaped env with placeholders rejected by policy.

### 3.4 Frontend gates

Staging pipeline frontend checks:

```text
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
```

Reason:

- `package-lock.json` is now committed;
- production Dockerfile uses `npm ci`;
- CI should match the production build path.

### 3.5 Docker image builds

Build images after app gates pass:

```text
docker build -f backend/Dockerfile.prod -t <registry>/automatedstructure-backend:<git_sha> backend
docker build -f frontend/Dockerfile.prod -t <registry>/automatedstructure-frontend:<git_sha> frontend
```

For pull requests:

- build images locally in CI;
- do not push images.

For approved staging releases:

- build images;
- push only to the approved registry after registry target and credentials are supplied;
- never use `latest` as the only deploy tag.

### 3.6 Image tagging strategy

Required tags:

```text
<git_sha>
master-<short_sha>
staging-candidate-<short_sha>
```

Optional tags:

```text
build-<run_number>
release-<semver_or_date>
```

Rules:

- deployments must reference immutable commit-SHA tags;
- `latest` may exist for convenience only, never as the sole release reference;
- record backend and frontend image digests in staging smoke evidence.

### 3.7 Image registry placeholder

Registry target is unresolved.

Placeholder:

```text
<approved-registry>/<account-or-org>/automatedstructure-backend:<git_sha>
<approved-registry>/<account-or-org>/automatedstructure-frontend:<git_sha>
```

If AWS remains target, likely registry is ECR:

```text
<aws_account_id>.dkr.ecr.<region>.amazonaws.com/automatedstructure-backend:<git_sha>
<aws_account_id>.dkr.ecr.<region>.amazonaws.com/automatedstructure-frontend:<git_sha>
```

No registry push is approved in P3-7d.

### 3.8 Migration task strategy

Before staging backend rollout:

1. Build approved backend image.
2. Start one-off migration task using the same backend image.
3. Inject staging DB secret refs through the approved secret path.
4. Run approved migration command.
5. Confirm Alembic head matches code head.
6. Stop if migration fails.
7. Record migration logs without secrets.

Do not run migrations from a developer machine against staging except under a documented emergency process.

### 3.9 Staging deployment approval gate

Use GitHub Environments or the approved CI/CD equivalent:

```text
Environment: staging
Required reviewers: deployment approver + migration approver
Required preconditions: all gates green + image digests available + staging secret refs configured
```

Deployment remains blocked until owner/operator values are supplied.

### 3.10 Staging smoke checklist

After staging deployment:

- `/health` returns 200;
- `/live` returns 200;
- `/ready` returns database ok, migrations up_to_date, redis ok;
- frontend reaches backend;
- Clerk staging login works if Clerk values exist;
- tenant/RLS smoke passes;
- Redis rate-limit smoke returns expected 429 behavior;
- controlled Redis-down smoke returns sanitized 503 behavior;
- mock billing gate smoke passes;
- send-gate dry-run passes only in mock/no-send mode;
- confirm no real send occurred;
- audit event smoke passes;
- logs checked for DSN/Redis/JWT/Clerk/provider secret leakage;
- smoke evidence attached before promotion.

### 3.11 Rollback path

Staging rollback must retain:

- previous backend image tag/digest;
- previous frontend image tag/digest;
- previous worker image/command if worker is active;
- previous task definition/release metadata;
- migration rollback plan or forward-fix decision.

Rollback requires rollback approver before use unless emergency-stop owner invokes an incident process.

---

## 4. Proposed production CI/CD pipeline

Production pipeline must be manual and gated.

Production promotion requires:

- staging smoke evidence passed;
- launch blockers cleared or explicitly owner-accepted;
- security/legal/billing/backup evidence attached;
- owner production cutover approval;
- migration approver approval;
- rollback approver approval;
- alert recipients confirmed;
- incident/emergency-stop owner confirmed;
- no placeholder secrets;
- secrets from approved secret path only;
- production boot guard fail-closed behavior preserved;
- no real-send/Stripe/SMS/live scraping unless separately approved.

Production sequence:

1. Select immutable image digests from staging-approved build.
2. Confirm production secret refs exist and are non-placeholder.
3. Run production preflight: config, auth, DB role, Redis, migrations, RLS, boot guard.
4. Run migration one-off task with production approval.
5. Deploy backend/worker/frontend through controlled rollout.
6. Run `/health`, `/live`, `/ready` checks.
7. Run protected API, tenant/RLS, billing-gate, and no-send smoke.
8. Monitor logs/metrics/alerts.
9. Record evidence and owner signoff.

Production must not include:

- Resend/live delivery unless P3-5f+ gates and final approval clear;
- Stripe money movement unless first-paying-client billing approval clears;
- SMS;
- live scraping;
- public launch without go/no-go signoff.

---

## 5. Required pipeline checks

### Backend

Required:

- Ruff;
- Black `--check`;
- mypy;
- pytest;
- Alembic migration smoke;
- Alembic current-head check if possible;
- production backend Docker build.

Recommended commands:

```text
cd backend
python -m ruff check app tests
python -m black --check app tests
python -m mypy app --ignore-missing-imports
python -m pytest
alembic upgrade head
alembic downgrade base
alembic upgrade head
docker build -f backend/Dockerfile.prod -t automatedstructure-backend:<git_sha> backend
```

### Frontend

Required:

- `npm ci`;
- lint;
- typecheck;
- test;
- build;
- production frontend Docker build.

Recommended commands:

```text
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:<git_sha> frontend
```

### Security / safety

Required:

- secret scan;
- changed-file guard for real `.env` files;
- changed-file guard for provider/live-send enablement;
- changed-file guard for production mock-provider exception;
- dependency audit captured as evidence but not auto-fixed without approval;
- no raw secret values in logs or artifacts;
- no Docker registry push except in approved release job;
- no deployment except through approved environment gate.

Suggested guards:

```text
fail if real .env files changed
fail if LIVE_EMAIL_SENDING_ENABLED=true appears without approved P3-5 evidence
fail if EMAIL_PROVIDER=resend appears in runtime config without approved P3-5 implementation gate
fail if MOCK_* production exception appears without controlled_demo owner attestation
fail if Stripe/SMS/live scraping enablement appears without recorded owner approval
```

---

## 6. Deployment safety gates

Required gates:

1. Staging deployment approval.
2. Migration approval.
3. Rollback approval.
4. Production cutover approval.
5. Emergency-stop owner confirmation.
6. Alert recipient confirmation.
7. Staging smoke evidence before promotion.
8. Launch-blocker review before production.
9. Legal/provider/billing approval before any live external send or money movement.

No gate can be skipped by a successful build alone.

---

## 7. Artifact / image strategy

Images:

- backend image: `backend/Dockerfile.prod`;
- frontend image: `frontend/Dockerfile.prod`;
- worker image: reuse backend image with approved command override after worker entrypoint is finalized.

Tags:

- required: commit SHA;
- recommended: run number + staging candidate label;
- not acceptable: latest-only deploy.

Evidence:

- record image tags;
- record image digests;
- record source commit;
- record workflow run ID;
- record migration task ID/log pointer;
- record smoke result pointer.

P3-7d does not push images.

---

## 8. Staging smoke evidence requirements

Staging smoke evidence bundle must include:

- source commit SHA;
- backend image tag/digest;
- frontend image tag/digest;
- worker image/command if active;
- migration result;
- `/health` result;
- `/live` result;
- `/ready` result with database ok, migrations up_to_date, redis ok;
- frontend-to-backend call proof;
- tenant/RLS smoke proof;
- rate-limit Redis 429 proof;
- Redis-down sanitized 503 proof;
- mock billing gate proof;
- send-gate dry-run only proof;
- confirmation no real send occurred;
- audit event proof;
- log review proof showing no secret leakage;
- rollback target recorded.

---

## 9. Remaining owner / operator values

Still needed before CI/CD implementation or staging release:

- GitHub environment names;
- registry target;
- AWS account ID;
- AWS region;
- ECS/ECR or approved deployment platform;
- staging frontend domain;
- staging API domain;
- DNS/TLS owner;
- secrets owner;
- KMS owner/path;
- RDS owner/sizing;
- Redis owner/sizing;
- deployment approver;
- migration approver;
- rollback approver;
- production cutover approver;
- emergency-stop owner;
- alert recipients;
- Clerk staging values;
- confirmation Resend remains disabled until P3-5f+ gates clear.

---

## 10. Final verdict

P3-7d is complete as a CI/CD release pipeline plan.

Implementation remains blocked until the owner/operator values above are supplied and a later slice explicitly approves workflow/pipeline changes.
