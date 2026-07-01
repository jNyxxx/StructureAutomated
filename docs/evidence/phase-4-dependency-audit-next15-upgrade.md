# P4-DepAudit-Fix-3a — Controlled Next.js 15 Upgrade Attempt

**Purpose:** Attempt the owner-approved Next.js 14 → 15 framework upgrade to clear remaining frontend dependency audit findings.
**Slice:** P4-DepAudit-Fix-3a
**Date:** 2026-07-01
**Status:** BLOCKED — Next 15.5.16 reduced audit findings but did not clear the dependency blocker.
**Branch:** `p4/next15-upgrade`
**Base branch:** `master`
**Preflight HEAD:** `0741887 docs(p4): add monitoring alerts incident plan`

---

## 1. William approval summary

William approved attempting the controlled Next.js 15 upgrade while the system is still local.

William also explicitly paused:

- AWS provisioning;
- deployment;
- registry/image publishing;
- staging enablement;
- provider setup;
- production rollout.

Production waits until the first real client is being closed. Boss demo/local work remains allowed.

No AWS, deployment, registry push, staging enablement, production enablement, real provider setup, secrets, Resend/live sending, cold outreach live sending, Stripe money movement, SMS, or live scraping work was performed in this slice.

---

## 2. Preflight result

| Check | Result |
|---|---|
| `git fetch origin` | PASS |
| `git checkout master` | PASS |
| `git pull --ff-only origin master` | PASS — already up to date |
| `git status --short` | PASS — clean before branch |
| `git log --oneline -20` | PASS — inspected |
| `HEAD == origin/master` | PASS — both `074188745d0e5c0dca3eec9fb8461252fd839980` |
| `.git` lock files | PASS — none found |
| Branch creation | PASS — `p4/next15-upgrade` |

Important catch-up note: the handoff said latest pushed commit was `477d577 docs(p4): plan framework dependency audit upgrade`, but the actual current `origin/master` was newer: `0741887 docs(p4): add monitoring alerts incident plan`. Work continued from the true current `origin/master`.

---

## 3. Codebase state scanned before changes

Reviewed the required frontend and planning files before attempting the package change:

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/next.config.mjs`
- `frontend/tsconfig.json`
- `frontend/app`
- `frontend/components`
- `frontend/lib`
- `frontend/Dockerfile.prod`
- `.github/workflows/ci.yml`
- `docs/evidence/phase-4-dependency-audit-fix-3-framework-upgrade-plan.md`
- `docs/PHASE_4_IMPLEMENTATION_PLAN.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`

Observed app surface:

- Frontend App Router pages cover auth, dashboard, prospects/import, campaigns/campaign detail/campaign drafts, draft/evidence, review queue, deliverability/send-gate, outcomes, audit logs, billing/access, settings/compliance/suppressions/team/security/integrations, and privacy.
- Frontend has 30 app files, 133 component files, and 13 lib files under the inspected paths.
- Backend has app/repository/service/router/schema/model coverage for auth, billing, campaigns, compliance, contacts/imports, deliverability, drafts, followups, outcomes, review, sending, settings, webhooks, rate limits, observability, workers, and provider boundaries.

---

## 4. Before audit summary

Before the attempted upgrade, `npm audit --json` from `frontend/` reported:

| Metric | Count |
|---|---:|
| Total findings | 5 |
| Critical | 0 |
| High | 4 |
| Moderate | 1 |

Remaining groups before upgrade:

1. Next/PostCSS runtime group.
2. Next lint-chain group through `eslint-config-next`, `@next/eslint-plugin-next`, and `glob`.

This matched P4-DepAudit-Fix-3-Plan.

---

## 5. Package change attempted

Allowed command run from `frontend/`:

```text
npm install next@15.5.16 eslint-config-next@15.5.16
```

Install output summary:

- added 7 packages;
- removed 32 packages;
- changed 8 packages;
- audited 582 packages;
- npm still reported 2 vulnerabilities after install.

Version changes observed after install:

| Package / field | Previous | Attempted new |
|---|---:|---:|
| `frontend/package.json` `next` | `^14.2.0` | `^15.5.16` |
| lockfile resolved `next` | `14.2.35` | `15.5.16` |
| `frontend/package.json` `eslint-config-next` | `^14.2.0` | `^15.5.16` |
| lockfile resolved `eslint-config-next` | `14.2.35` | `15.5.16` |
| lockfile resolved `@next/eslint-plugin-next` | `14.2.35` | `15.5.16` |
| React dependency range | `^18.3.0` | unchanged |
| lockfile resolved React | `18.3.1` | unchanged |
| Next Node engine | `>=18.17.0` | `^18.18.0 || ^19.8.0 || >= 20.0.0` |

React did not change. The Node requirement changed but remains compatible with the repo's Node 20 CI/Docker path.

---

## 6. Frontend gate results on attempted Next 15.5.16 state

| Gate | Result | Notes |
|---|---|---|
| `npm ci` | PASS | Reinstalled 581 packages; npm reported 2 vulnerabilities. |
| `npm run lint` | PASS | No ESLint warnings/errors. Next 15 printed a deprecation warning that `next lint` will be removed in Next 16. |
| `npm run typecheck` | PASS | `tsc --noEmit` passed. |
| `npm run test` | PASS | 141 tests passed across 4 files. Existing expected stderr appeared for mocked network-fallback cases and jsdom navigation limitation. |
| `npm run build` | PASS | Next 15.5.16 compiled successfully; 27 static pages generated. |
| `npm audit` | FAIL | 2 vulnerabilities remained: 1 high, 1 moderate. |
| `npm audit --json > docs/evidence/phase-4-dependency-audit-after-next15.json` | PASS via captured JSON evidence | Redirection was not used through the shell; JSON evidence was captured and written to the evidence file. |

---

## 7. After audit summary

After the attempted Next 15.5.16 upgrade, `npm audit` reported:

| Metric | Count |
|---|---:|
| Total findings | 2 |
| Critical | 0 |
| High | 1 |
| Moderate | 1 |

Remaining findings:

| Package | Severity | Summary | Affected range reported by audit |
|---|---|---|---|
| `next` | High | Middleware / Proxy bypass in App Router applications via segment-prefetch routes — incomplete fix follow-up | `>=15.2.0 <15.5.18` |
| `postcss` nested under `next` | Moderate | XSS via unescaped `</style>` in CSS stringify output | `<8.5.10` |

The upgrade improved the audit count from 5 to 2, but did not clear the dependency blocker.

| Blocker | Result |
|---|---|
| Staging dependency blocker | Still open |
| Production dependency blocker | Still open |

---

## 8. Backend gate results

William-required backend gates were run from `backend/`:

| Gate | Result | Notes |
|---|---|---|
| `python -m ruff check app tests` | PASS | All checks passed. |
| `python -m black --check app tests` | PASS | 214 files would be left unchanged. |
| `python -m mypy app --ignore-missing-imports` | PASS | No issues in 156 source files. |
| `python -m pytest -q` | PASS | Test suite completed with one existing Starlette/httpx deprecation warning. |

---

## 9. Docker verification

Command attempted from repo root:

```text
docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:next15-local frontend
```

Result: NOT RUNNING / ENVIRONMENT BLOCKED.

Docker Desktop/Linux engine was unavailable:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

This is an environment/daemon availability issue, not a Next.js compatibility result. Since `npm audit` had already failed, this did not change the slice verdict.

---

## 10. Browser smoke

Local browser demo smoke was not completed for the attempted Next 15 state because the dependency audit gate failed and the upgrade was reverted per blocker rules.

The Next 15 build did pass before rollback, but the local browser smoke path is not accepted as complete evidence for this slice.

Required smoke path remains:

- login page;
- demo login;
- dashboard;
- contacts/prospects;
- campaign flow;
- draft/evidence/review queue;
- send-gate dry run;
- mock send intent;
- audit trail;
- billing/access UI;
- compliance/suppression UI;
- logout/login again.

---

## 11. Rollback result

Because `npm audit` failed after the Next 15.5.16 attempt, package/source changes were reverted.

Reverted:

- `frontend/package.json`
- `frontend/package-lock.json`
- auto-generated `frontend/next-env.d.ts` changes from the Next 15 build

Restored local frontend install after rollback:

```text
cd frontend
npm ci
```

Rollback install result: PASS. The repo returned to the pre-upgrade package state with the known 5 vulnerability baseline.

Final intended branch scope is docs/evidence only.

---

## 12. Issues found

1. The owner-approved exact target `next@15.5.16` is no longer enough to clear all audit findings.
2. NPM audit now reports a remaining Next advisory affecting `>=15.2.0 <15.5.18`.
3. NPM audit still reports the nested PostCSS advisory under Next.
4. `next lint` remains functional on Next 15 but prints a deprecation warning for future Next 16.
5. Docker Desktop/Linux engine was unavailable for the required frontend production Docker build.
6. Browser smoke was not completed because the upgrade had to be rolled back after audit failure.

---

## 13. Remaining blockers

- Dependency blocker remains open because `next@15.5.16` did not clear audit.
- Staging/AWS values remain paused by William.
- Deployment remains paused.
- Registry/image push remains paused.
- Live providers remain paused.
- Production waits for first real client.
- Docker verification requires Docker Desktop/Linux engine to be running in a future verification session.
- Browser smoke remains required if a future approved upgrade clears audit and is retained.

---

## 14. Recommendation

| Question | Recommendation |
|---|---|
| Boss demo remains allowed? | Yes. The failed upgrade was rolled back; local/mock boss demo remains allowed under the existing controlled-demo constraints. |
| Dependency blocker cleared? | No. It improved from 5 to 2 findings, but blocker remains open. |
| Staging allowed? | No. Staging remains paused by William and dependency blocker is still open. |
| Production allowed? | No. Production waits for first real client and remains blocked by owner/operator/provider/deployment/legal readiness gates. |
| Next dependency path | Ask William to approve a revised Next 15 patch target that satisfies audit, likely `next >=15.5.18` with aligned `eslint-config-next`, or formally accept risk. Do not jump to Next 16 unless separately approved. |
| Package state to keep now | Keep rollback. Do not retain `next@15.5.16` because it does not clear audit. |

---

## 15. Final verdict

- P4-DepAudit-Fix-3a: **BLOCKED**.
- Boss demo: **allowed**.
- Dependency blocker: **still open**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
- Package/source changes: **reverted**.
- Evidence kept: `docs/evidence/phase-4-dependency-audit-next15-upgrade.md` and `docs/evidence/phase-4-dependency-audit-after-next15.json`.
