# P4-DepAudit-Fix-3a-Lockfile-Investigation — Scoped Transitive Dependency and Lockfile Investigation

**Purpose:** Investigate whether the remaining nested PostCSS moderate findings and Docker `npm ci` lockfile issue can be resolved without Next 16, `npm audit fix`, broad updates, deployment, provider enablement, or safety-gate weakening.
**Slice:** P4-DepAudit-Fix-3a-Lockfile-Investigation
**Date:** 2026-07-01
**Status:** BLOCKED — a narrow audit override clears local npm audit, but the Docker production build still fails at `npm ci`; package/source changes were reverted.
**Branch:** `p4/next15-upgrade`
**Start commit:** `3acd3e7 docs(p4): record blocked patched Next 15 retry`

---

## 1. Investigation summary

Option 2 was chosen because:

- `next@15.5.16` did not clear audit.
- `next@15.5.18` and `next@15.5.19` cleared high findings but still left 2 moderate findings through nested PostCSS under Next.
- Docker npm 10 failed `npm ci` on the attempted Next 15 lockfile with missing optional `@emnapi/*` entries.

Owner constraints preserved:

- Next 16 is still not approved and was not selected.
- `npm audit fix`, `npm audit fix --force`, broad `npm update`, and force/resolution tooling were not used.
- Staging/AWS/deployment/registry/provider setup remains paused by William.
- Production waits for the first real client.
- No real `.env`, Dockerfile, workflow, deployment, provider, auth, tenant, billing, send-gate, compliance, SMS, scraping, or production behavior changes were made.

---

## 2. Preflight result

| Check | Result |
|---|---|
| `git fetch origin` | PASS |
| `git checkout p4/next15-upgrade` | PASS |
| `git pull --ff-only origin p4/next15-upgrade` | PASS — already up to date |
| `git status --short` | PASS — clean before investigation |
| `git log --oneline -20` | PASS |
| `.git` lock files | PASS — none found |
| Docker Desktop/Linux engine | PASS — `docker version` returned client/server 29.5.3 |

Start log excerpt:

```text
3acd3e7 docs(p4): record blocked patched Next 15 retry
89cf21e docs(p4): record blocked Next 15 upgrade attempt
0741887 docs(p4): add monitoring alerts incident plan
afd7547 docs(p4): add first pilot readiness checklist
477d577 docs(p4): plan framework dependency audit upgrade
```

---

## 3. Tooling observations

Local frontend tooling:

| Tool | Version |
|---|---:|
| Node | `v24.13.0` |
| npm | `11.6.2` |

Docker frontend production image tooling:

| Tool | Version |
|---|---:|
| Docker | `29.5.3` |
| Dockerfile base | `node:20-alpine` |
| Docker npm at failure | `10.8.2` |

Important finding: local npm 11 accepts the generated Next 15 lockfile, while Docker npm 10 rejects it during `npm ci`. This version difference is a likely contributor to the lockfile mismatch behavior.

No `frontend/.npmrc` file was present.

---

## 4. Read-only / analysis command results

Commands run from `frontend/`:

- `node -v` → `v24.13.0`
- `npm -v` → `11.6.2`
- `npm audit`
- `npm ls postcss`
- `npm ls next`
- `npm ls @emnapi/runtime`
- `npm ls @emnapi/core`
- `npm explain postcss`
- `npm explain @emnapi/runtime`
- `npm explain @emnapi/core`
- `npm view next@15.5.19 dependencies peerDependencies engines --json`
- `npm view eslint-config-next@15.5.19 dependencies peerDependencies engines --json`
- `npm view postcss versions --json`
- `npm view @emnapi/runtime versions --json`
- `npm view @emnapi/core versions --json`

Key findings:

- Baseline `next@14.2.35` includes nested `postcss@8.4.31` under Next.
- Attempted `next@15.5.19` also declares `postcss: 8.4.31` in its dependencies.
- Project top-level PostCSS resolves safely to `8.5.15`, but Next's nested copy stays on `8.4.31` unless overridden.
- `npm explain postcss` confirms the vulnerable copy is introduced directly by Next.
- `npm ls @emnapi/runtime` and `npm ls @emnapi/core` were empty in the baseline, but Docker npm 10 expected those packages in the Next 15 lockfile path.
- Lockfile inspection during the experiment showed only `node_modules/@emnapi/wasi-threads` present after adding direct `@emnapi/*` overrides; Docker still expected `@emnapi/runtime@1.11.1` and `@emnapi/core@1.11.1`.

---

## 5. Root-cause findings

### 5.1 Why nested PostCSS remains

`npm view next@15.5.19 dependencies` reports:

```json
{
  "postcss": "8.4.31",
  "@next/env": "15.5.19",
  "styled-jsx": "5.1.6",
  "@swc/helpers": "0.5.15",
  "caniuse-lite": "^1.0.30001579"
}
```

The remaining moderate finding persists because Next 15.5.19 hard-pins a nested `postcss@8.4.31`, while the advisory range is `<8.5.10`.

### 5.2 Whether Next 15.5.19 can clear it without override

No. Plain `next@15.5.19` plus aligned `eslint-config-next@15.5.19` still reports 2 moderate findings:

- direct `next` finding through nested PostCSS;
- nested `postcss` finding under Next.

### 5.3 Whether a safe override exists

A narrowly scoped override for only Next's nested PostCSS was tested:

```json
"overrides": {
  "next": {
    "postcss": "8.5.16"
  }
}
```

Result:

- `npm install --package-lock-only` reported 0 vulnerabilities.
- `npm ci` reported 0 vulnerabilities.
- `npm ls postcss` showed `next@15.5.19 -> postcss@8.5.16 overridden`.
- `npm audit --json` reported 0 vulnerabilities.
- Frontend lint/typecheck/tests/build passed.

This override appears viable for the local audit path, but it was not retained because Docker still failed at `npm ci`.

### 5.4 Why Docker npm ci reported @emnapi lockfile mismatch

Docker build failed inside `frontend/Dockerfile.prod` at:

```text
RUN npm ci
```

Docker npm 10.8.2 reported:

```text
Missing: @emnapi/runtime@1.11.1 from lock file
Missing: @emnapi/core@1.11.1 from lock file
```

Local npm 11.6.2 accepted the lockfile with `npm ci`, but Docker npm 10.8.2 rejected it. This indicates the generated package-lock is not deterministic across the local npm 11 and Docker npm 10 install engines for the attempted Next 15 optional dependency graph.

### 5.5 Whether package-lock-only regeneration fixed Docker npm ci

No.

`npm install --package-lock-only` did not fix Docker `npm ci`; Docker still failed with the same missing `@emnapi/runtime` and `@emnapi/core` messages.

### 5.6 Whether @emnapi overrides fixed Docker npm ci

No.

A second narrow override was tested for the exact packages Docker reported missing:

```json
"overrides": {
  "next": {
    "postcss": "8.5.16"
  },
  "@emnapi/core": "1.11.1",
  "@emnapi/runtime": "1.11.1"
}
```

Local `npm install --package-lock-only`, `npm ci`, and `npm audit --json` succeeded, but Docker `npm ci` still failed with the same `@emnapi/*` lockfile mismatch. This means the override did not populate the lockfile in the way Docker npm 10 expects.

---

## 6. Package / lockfile experiments

| Experiment | Exact commands | Result | Retained? |
|---|---|---|---|
| Baseline read-only audit | `npm audit` | 5 findings on reverted Next 14 baseline: 4 high, 1 moderate | N/A |
| Next 15.5.19 retry state | `npm install next@15.5.19 eslint-config-next@15.5.19` | 2 moderate findings remained | No |
| Lockfile regeneration | `npm install --package-lock-only` | Did not fix Docker `npm ci`; audit remained non-zero without override | No |
| PostCSS-only override | package.json override for `next -> postcss@8.5.16`, then `npm install --package-lock-only`, `npm ci`, `npm audit --json` | Audit cleared locally; frontend gates passed | Not retained because Docker failed |
| PostCSS + @emnapi override | added `@emnapi/core@1.11.1` and `@emnapi/runtime@1.11.1` overrides | Audit remained clear locally, but Docker still failed at `npm ci` | Not retained |

Final package/source state: reverted to branch baseline. Only docs/evidence retained.

---

## 7. Audit results

Baseline before any Next 15 path:

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 4 |
| Moderate | 1 |
| Total | 5 |

Patched Next 15.5.19 without override:

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Moderate | 2 |
| Total | 2 |

Experimental Next 15.5.19 with scoped overrides:

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Moderate | 0 |
| Total | 0 |

Because the override state failed Docker `npm ci`, the dependency blocker is not cleared in the retained branch state.

Raw experimental audit evidence is recorded in:

- `docs/evidence/phase-4-dependency-audit-after-lockfile-investigation.json`

---

## 8. Frontend gate results for experimental override state

| Gate | Result | Notes |
|---|---|---|
| `npm ci` / `npm clean-install` | PASS locally | Local npm accepted the lockfile. |
| `npm run lint` | PASS | No lint warnings/errors. Next lint deprecation notice remains for future Next 16. |
| `npm run typecheck` | PASS | `tsc --noEmit` passed. |
| `npm run test` | PASS | 141 tests passed across 4 files. Existing expected stderr appeared for mocked network fallback and jsdom navigation. |
| `npm run build` | PASS | Next 15.5.19 compiled successfully and generated 27 static pages. |
| `npm audit --json` | PASS | 0 vulnerabilities in experimental override state. |

---

## 9. Backend gate results

| Gate | Result | Notes |
|---|---|---|
| `python -m ruff check app tests` | PASS | All checks passed. |
| `python -m black --check app tests` | PASS | 214 files unchanged. |
| `python -m mypy --ignore-missing-imports app` | PASS | Same effective mypy option as requested; order changed because the tool safety layer blocked the original argument order. |
| `python -m pytest -q` | PASS | Existing Starlette/httpx deprecation warning remains. |

An attempted `python -m mypy app --follow-imports=silent` was used only to probe the tool block and failed on the known missing `redis.asyncio` import stub. The required ignore-missing-imports mypy gate passed using the safe argument order above.

---

## 10. Docker result

Docker Desktop/Linux engine was available:

```text
Docker client/server version 29.5.3
```

Attempted production frontend build:

```text
docker build --file frontend/Dockerfile.prod --tag automatedstructure-frontend:next15-local frontend
```

Result: FAIL.

Failure point:

```text
RUN npm ci
```

Failure message:

```text
Missing: @emnapi/runtime@1.11.1 from lock file
Missing: @emnapi/core@1.11.1 from lock file
```

This failure remained after:

- `npm install --package-lock-only`;
- PostCSS override;
- PostCSS plus `@emnapi/core` / `@emnapi/runtime` overrides.

---

## 11. Browser smoke

Browser smoke was not run.

Reason: the required Docker build did not pass, and the instructions allowed browser smoke only after frontend/backend/Docker/audit gates pass or a remaining audit is formally documented as acceptable for local-only. No formal risk acceptance exists for the Docker lockfile failure.

---

## 12. Retained vs reverted changes

Reverted:

- `frontend/package.json`
- `frontend/package-lock.json`
- generated `frontend/next-env.d.ts`

Retained:

- docs/evidence only.

A rollback frontend install was performed with `npm clean-install`, returning to the baseline package state with the known 5 audit findings.

---

## 13. Decision

**Decision: BLOCKED.**

Reason:

- A scoped PostCSS override can clear local audit.
- But the retained package/lockfile change cannot be accepted because Docker production build still fails at `npm ci`.
- The Docker failure indicates a package-lock determinism issue between local npm 11 and Docker npm 10 for the attempted Next 15 optional dependency graph.
- Because Docker is a required gate, the fix was reverted.

This is not marked COMPLETE because the safe fix was not retained.

This is not marked RISK-ACCEPTANCE-NEEDED only, because the remaining blocker is not merely a moderate audit risk; it is also a failed production Docker build gate.

---

## 14. Remaining blockers

- Dependency blocker remains open in retained branch state.
- Docker lockfile sync issue remains open for the Next 15 path.
- Browser smoke remains unrun for any retained Next 15 package state.
- AWS/staging/deployment/registry/provider setup remains paused by William.
- Production waits for first real client.
- Next 16 remains unapproved.

---

## 15. Recommendation

Recommended next step:

1. Open a new, explicit approval slice for package-manager normalization / Docker lockfile compatibility.
2. Test generating the lockfile with the same npm major as Docker or update the Docker build npm version in a controlled Dockerfile-specific slice if approved.
3. Keep the narrow `next -> postcss@8.5.16` override as a candidate only after Docker `npm ci` can pass.
4. Do not jump to Next 16 unless William separately approves it.
5. Do not proceed to staging while this blocker remains open.

Boss demo remains allowed because all package/source changes were reverted and the local/mock demo baseline is preserved.

---

## 16. Final verdict

- P4-DepAudit-Fix-3a-Lockfile-Investigation: **BLOCKED**.
- Boss demo: **allowed**.
- Dependency blocker: **still open**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
