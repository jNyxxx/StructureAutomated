# P3-7b — Production Dockerfile Hardening

**Purpose:** Add production-oriented backend/frontend image definitions and build-context exclusions without changing local dev flow or enabling deployment.
**Status:** Complete with Docker daemon unavailable limit recorded.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `c99ad5c docs(p3-7): plan deployment and ops readiness`

---

## 1. Scope and hard stop

P3-7b hardens production Docker build/runtime structure only.

Confirmed not done:

- no deployment;
- no AWS provisioning;
- no production enablement;
- no real `.env` file edit;
- no secrets added;
- no Resend adapter, SDK, or API call;
- no live email sending;
- no Stripe, SMS, or live scraping;
- no boot-guard weakening;
- no auth/RBAC/RLS/tenant-isolation changes;
- no billing or send-gate bypass;
- no image push to any registry.

---

## 2. Files changed

Changed Docker/build files:

- `backend/Dockerfile.prod` — new production backend image.
- `frontend/Dockerfile.prod` — new production frontend image.
- `backend/.dockerignore` — hardened build-context exclusions.
- `frontend/.dockerignore` — hardened build-context exclusions.
- `frontend/next.config.mjs` — added `output: "standalone"` for production runtime image.

Changed docs:

- `docs/evidence/phase-3-7b-production-dockerfile-hardening.md` — this evidence.
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

Local dev Dockerfiles and `docker-compose.yml` were preserved.

---

## 3. Backend production Docker strategy

Added `backend/Dockerfile.prod`.

Design:

- multi-stage build;
- builder stage uses `python:3.12-slim` and builds wheels from existing `pyproject.toml` project metadata;
- runtime stage uses `python:3.12-slim`;
- installs runtime dependencies only, not `[dev]` extras;
- no `--reload`;
- no development server command;
- runs the production ASGI command:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Security/runtime properties:

- non-root runtime user `app`;
- runtime configuration comes from environment values only;
- no `.env` files copied;
- no secrets baked into image layers;
- production boot guard remains active through `app.main` lifespan;
- exposes port `8000`;
- includes source + Alembic files under `/app` so migration-head readiness checks keep the expected repo-style layout.

---

## 4. Frontend production Docker strategy

Added `frontend/Dockerfile.prod`.

Design:

- multi-stage build;
- dependency stage uses `npm ci` against existing `package-lock.json`;
- builder stage runs `npm run build`;
- runtime stage uses Next.js standalone output;
- no `next dev`;
- runtime command:

```text
node server.js
```

Security/runtime properties:

- non-root runtime user `nextjs`;
- no `.env` files copied;
- no secrets baked into image layers;
- exposes port `3000`;
- `NEXT_TELEMETRY_DISABLED=1` set in image stages;
- only runtime-safe public env should be supplied at deploy time.

Small config change:

```text
next.config.mjs -> output: "standalone"
```

This enables the runtime image to copy `.next/standalone` instead of shipping the dev server or full source tree.

---

## 5. Worker runtime strategy

No unsupported worker behavior was invented.

Current state:

- `backend/app/workers/worker.py` contains the testable `WorkerLoop` class.
- `QueueService` supports claim/process lifecycle and tenant-scoped job execution.
- `docker-compose.yml` worker command is still a local placeholder.

Production strategy:

- future worker service should reuse the backend production image;
- worker should run with a command override only after a supported worker entrypoint exists;
- no separate worker Dockerfile was created in P3-7b;
- no real provider/send/Stripe/SMS/live-scraping worker path was enabled.

Remaining worker blocker:

- add an approved worker entrypoint/command in a later slice before staging service creation.

---

## 6. `.dockerignore` / security exclusions

Backend `.dockerignore` now excludes:

- `.env`, `.env.*`;
- Python bytecode/caches;
- virtualenvs;
- build/dist/wheel artifacts;
- pytest/mypy/ruff/coverage caches;
- editor/OS noise;
- logs/temp files;
- local runtime data volumes.

Frontend `.dockerignore` now excludes:

- `.env`, `.env.*`;
- `node_modules`;
- `.next`, `out`, coverage/test artifacts;
- package-manager/tooling caches;
- TypeScript/Vitest artifacts;
- editor/OS noise;
- logs/temp files.

`!.env.example` remains allowed, but production Dockerfiles do not copy it.

---

## 7. Backend gate results

Command:

```text
python -m ruff check app tests && python -m black --check app tests && python -m mypy app --ignore-missing-imports && python -m pytest
```

Result:

```text
ruff PASS
black PASS — 203 files would be left unchanged
mypy PASS — no issues found in 151 source files
pytest PASS — 638 passed, 1 warning in 36.49s
```

Known warning:

- existing FastAPI/Starlette `TestClient` deprecation warning.

---

## 8. Frontend gate results

Command:

```text
npm run lint && npm run typecheck && npm run test && npm run build
```

Result:

```text
lint PASS — no ESLint warnings or errors
typecheck PASS
test PASS — 122 passed
build PASS — Next.js 14.2.35 compiled successfully, generated 27 static pages, standalone trace collected
```

Known warning/noise:

- existing Vite CJS deprecation warning;
- expected test stderr for backend-unavailable fallback paths.

---

## 9. Docker build result

Attempted:

```text
docker --version
docker build -f backend/Dockerfile.prod -t automatedstructure-backend:p3-7b-prod backend
docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:p3-7b-prod frontend
```

Result:

```text
Docker version 29.5.3, build d1c06ef
Docker build BLOCKED — Docker CLI exists, but the Docker Desktop/Linux engine was not running.
Error: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

Honest limit:

- Production Dockerfiles were created and app/frontend gates passed, but local Docker image build validation must be rerun after Docker Desktop / the Linux engine is started.
- No image was pushed to any registry.

---

## 10. Remaining deployment blockers

Still blocked before staging/prod release:

- Docker daemon/build validation rerun;
- worker entrypoint/command;
- AWS account and region;
- deployment platform decision;
- staging frontend/API domains;
- TLS/ACM/DNS owner;
- Secrets Manager/KMS owner and paths;
- RDS/Postgres owner/config;
- Redis/ElastiCache owner/config;
- backup retention/RPO/RTO;
- alert recipients;
- CI/CD/migration/rollback approvers;
- production cutover approver;
- Clerk staging values;
- confirmation that Resend stays disabled until P3-5f+ gates clear.

---

## 11. Safety confirmation

Confirmed:

- no deployment;
- no production enabled;
- no real `.env` file changed;
- no secrets added;
- no Resend/live sending enabled;
- no Stripe/SMS/live scraping enabled;
- no provider SDK added;
- no Resend API call added;
- no image registry push;
- boot guard not weakened;
- auth/RBAC/RLS/tenant isolation not changed;
- billing/send gates not bypassed.

---

## 12. Final verdict

P3-7b production Dockerfile hardening is complete.

The only blocker is Docker image build validation: Docker Desktop/Linux engine must be started, then the two production image build commands should be rerun before P3-7c/P3-7d use these images in staging plans.
