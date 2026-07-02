# P4-DepAudit-Fix-3a-Retry — Revised Patched Next.js 15 Upgrade Attempt

**Purpose:** Retry the owner-approved Next.js 15 upgrade using a patched 15.x target, without selecting Next 16.
**Slice:** P4-DepAudit-Fix-3a-Retry
**Date:** 2026-07-01
**Status:** BLOCKED — patched Next 15 removed high findings but did not produce a clean audit, and the frontend production Docker build failed.
**Branch:** `p4/next15-upgrade`
**Starting commit:** `89cf21e docs(p4): record blocked Next 15 upgrade attempt`

---

## 1. Retry reason and owner direction

The previous exact target, `next@15.5.16` with `eslint-config-next@15.5.16`, did not clear audit. It reduced the original 5 findings to 2 findings, but still left 1 high Next advisory and 1 moderate nested PostCSS advisory.

Owner direction for this retry was to use a revised patched Next 15 target, likely `15.5.18` or newer if required, while keeping `eslint-config-next` aligned and avoiding Next 16 unless separately approved.

No deployment, AWS, registry push, staging enablement, production enablement, live provider enablement, real billing, SMS, live scraping, `.env` edit, or safety-gate weakening was performed.

---

## 2. Preflight result

| Check | Result |
|---|---|
| `git fetch origin` | PASS |
| `git checkout p4/next15-upgrade` | PASS |
| `git pull --ff-only origin p4/next15-upgrade` | PASS |
| `git status --short` | PASS — clean before retry |
| `git log --oneline -20` | PASS |
| `.git` lock files | PASS — none reported |

Start of branch log:

```text
89cf21e docs(p4): record blocked Next 15 upgrade attempt
0741887 docs(p4): add monitoring alerts incident plan
afd7547 docs(p4): add first pilot readiness checklist
477d577 docs(p4): plan framework dependency audit upgrade
1de5112 docs(p4): record remaining dependency audit blocker
```

---

## 3. Inspected files

Inspected before retry:

- `docs/evidence/phase-4-dependency-audit-next15-upgrade.md`
- `docs/evidence/phase-4-dependency-audit-after-next15.json`
- `docs/evidence/phase-4-dependency-audit-fix-3-framework-upgrade-plan.md`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/next.config.mjs`
- `frontend/tsconfig.json`
- `frontend/app`
- `frontend/components`
- `frontend/lib`
- `frontend/Dockerfile.prod`
- `.github/workflows/ci.yml`

Baseline before retry remained Next 14:

- `next` range: `^14.2.0`, resolved `14.2.35`
- `eslint-config-next` range: `^14.2.0`, resolved `14.2.35`
- React resolved `18.3.1`

---

## 4. Patched Next 15 target selection

NPM metadata showed stable aligned 15.x candidates through `15.5.19`. The smallest candidate satisfying the previous high advisory range was `15.5.18`, and matching `eslint-config-next@15.5.18` exists.

Because `15.5.18` still left the nested PostCSS moderate finding, the latest available stable 15.x pair, `15.5.19`, was also tested. No stable `15.6.x` target was found from the queried metadata. Next 16 was not selected.

---

## 5. Package changes attempted

First attempted:

```text
npm install next@15.5.18 eslint-config-next@15.5.18
```

Then tested latest available stable 15.x:

```text
npm install next@15.5.19 eslint-config-next@15.5.19
```

Observed final attempted state:

| Package / field | Previous | Attempted |
|---|---:|---:|
| `next` root range | `^14.2.0` | `^15.5.19` |
| resolved `next` | `14.2.35` | `15.5.19` |
| `eslint-config-next` root range | `^14.2.0` | `^15.5.19` |
| resolved `eslint-config-next` | `14.2.35` | `15.5.19` |
| resolved `@next/eslint-plugin-next` | `14.2.35` | `15.5.19` |
| React | `18.3.1` | unchanged |
| Next Node engine | `>=18.17.0` | `^18.18.0 || ^19.8.0 || >= 20.0.0` |

React did not change. The Node requirement remains compatible with Node 20.

---

## 6. Before audit summary

Before the original Next attempt:

| Metric | Count |
|---|---:|
| Total findings | 5 |
| Critical | 0 |
| High | 4 |
| Moderate | 1 |

After the failed `15.5.16` attempt:

| Metric | Count |
|---|---:|
| Total findings | 2 |
| Critical | 0 |
| High | 1 |
| Moderate | 1 |

Remaining groups after `15.5.16` were the high Next advisory and the nested PostCSS moderate advisory.

---

## 7. After audit summary

After patched retry on `15.5.19`, `npm audit --json` reported:

| Metric | Count |
|---|---:|
| Total findings | 2 |
| Critical | 0 |
| High | 0 |
| Moderate | 2 |

Remaining group:

- nested PostCSS moderate finding under `node_modules/next/node_modules/postcss`
- direct `next` finding only because it depends on that nested PostCSS copy

Interpretation:

- Patched Next 15 cleared all high findings.
- Patched Next 15 did not produce a clean audit.
- npm's suggested automated fix is not acceptable because it requires a forced breaking action and would not preserve the approved Next 15 path.
- Dependency blocker remains open unless William/security formally accepts the remaining moderate risk or approves a separate scoped mitigation.

---

## 8. Frontend gate results on attempted `15.5.19` state

| Gate | Result | Notes |
|---|---|---|
| `npm ci` | PASS | Reinstalled 581 packages; npm reported 2 moderate findings. |
| `npm run lint` | PASS | No ESLint warnings/errors. `next lint` deprecation notice for future Next 16 remains. |
| `npm run typecheck` | PASS | Typecheck passed. |
| `npm run test` | PASS | 141 tests passed across 4 files. Existing expected stderr appeared for mocked network-fallback and jsdom navigation cases. |
| `npm run build` | PASS | Next 15.5.19 compiled successfully and generated 27 static pages. |
| `npm audit` | FAIL | 2 moderate findings remained. |
| audit JSON evidence | PASS captured | Written to `docs/evidence/phase-4-dependency-audit-after-next15-retry.json`. |

---

## 9. Backend gate results

| Gate | Result |
|---|---|
| `python -m ruff check app tests` | PASS |
| `python -m black --check app tests` | PASS |
| `python -m mypy app --ignore-missing-imports` | PASS |
| `python -m pytest -q` | PASS |

Backend pytest completed with the existing Starlette/httpx deprecation warning.

---

## 10. Docker verification

Docker Desktop/Linux engine was running.

Attempted:

```text
docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:next15-retry-local frontend
```

Result: FAIL.

Failure point: Docker build failed at the `RUN npm ci` layer inside `frontend/Dockerfile.prod`.

Docker npm reported package/lockfile sync failure and missing transitive optional entries:

```text
Missing: @emnapi/runtime@1.11.1 from lock file
Missing: @emnapi/core@1.11.1 from lock file
```

Local Windows `npm ci` passed, but Docker `npm ci` under `node:20-alpine` did not. This requires separate lockfile/package-manager investigation and cannot be forced in this retry.

---

## 11. Browser smoke

Browser smoke was not run because `npm audit` failed and the frontend production Docker build failed. The instruction allowed browser smoke only after frontend gates and Docker build pass.

Unrun smoke path: login, demo login, dashboard, prospects, campaign flow, draft/evidence/review queue, send-gate dry run, mock send intent, audit trail, billing/access UI, compliance/suppression UI, and logout/login again.

---

## 12. Rollback result

Because audit still failed and Docker build failed, package/source changes were reverted.

Reverted:

- `frontend/package.json`
- `frontend/package-lock.json`
- generated `frontend/next-env.d.ts` change from Next build

Rollback install:

```text
cd frontend
npm ci
```

Rollback result: PASS. Baseline returned to the known Next 14 package state with the original 5 audit findings.

Final retained branch scope: docs/evidence only.

---

## 13. Issues found

1. `next@15.5.18` is the smallest patched stable Next 15 target satisfying the previous high advisory range, but it still leaves the nested PostCSS moderate finding.
2. `next@15.5.19` is the latest stable Next 15 target found and tested, but it also leaves the nested PostCSS moderate finding.
3. No stable `15.6.x` target was found from npm metadata.
4. `npm audit` still exits non-zero with 2 moderate findings on patched Next 15.
5. Docker build fails at `npm ci` due to package-lock sync behavior for transitive optional entries.
6. Browser smoke was not eligible because audit and Docker gates did not pass.

---

## 14. Remaining blockers

- Dependency blocker still open: high findings are gone on patched Next 15, but 2 moderate audit findings remain.
- Staging/AWS/deployment/registry/provider setup remains paused by William.
- Production waits for first real client.
- Docker package-lock sync issue must be investigated before retaining a future framework upgrade.
- Browser smoke remains required after a future retained upgrade has passing frontend gates and Docker build.
- Any transitive override or package-manager/lockfile correction needs separate approval because this retry only approved a patched Next 15 package pair.

---

## 15. Recommendation

| Question | Recommendation |
|---|---|
| Boss demo allowed? | Yes. Package/source changes were reverted; existing local/mock boss demo remains allowed. |
| Dependency blocker cleared? | No. High findings are cleared by the candidate, but audit is not clean and Docker failed. |
| Staging allowed? | No. Staging remains paused by William and dependency blocker remains open. |
| Production allowed? | No. Production waits for first real client and remains blocked by owner/operator/provider/deployment/legal readiness gates. |
| Next 15 path | Do not keep this retry as an upgrade. Document it as blocked. |
| Next 16 path | Do not jump to Next 16 without separate approval. |
| Recommended owner decision | Ask William/security to choose: accept the remaining moderate nested PostCSS finding with compensating controls, approve a scoped transitive dependency/lockfile investigation, or approve Next 16 migration planning. |

---

## 16. Final verdict

- P4-DepAudit-Fix-3a-Retry: **BLOCKED**.
- Boss demo: **allowed**.
- Dependency blocker: **still open**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
- Package/source changes: **reverted**.
- Evidence kept:
  - `docs/evidence/phase-4-dependency-audit-next15-retry.md`
  - `docs/evidence/phase-4-dependency-audit-after-next15-retry.json`
