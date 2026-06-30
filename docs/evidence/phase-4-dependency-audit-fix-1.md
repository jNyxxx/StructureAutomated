# P4-DepAudit-Fix-1 — Safe Targeted Dev Dependency Fixes

**Purpose:** Apply the first controlled dependency audit fix for frontend dev/test tooling only.
**Slice:** P4-DepAudit-Fix-1
**Date:** 2026-06-30
**Status:** Complete — targeted frontend package update. No app source changes, no backend changes, no deployment, no AWS provisioning, no registry push, no live providers, no real billing, no production enablement.
**Base commit:** `71cf830 docs(p4): add dependency audit triage plan`
**Before evidence:** [phase-4-dependency-audit-triage-plan](phase-4-dependency-audit-triage-plan.md) · [phase-4-dependency-audit-raw.json](phase-4-dependency-audit-raw.json)
**After evidence:** [phase-4-dependency-audit-after-fix-1.json](phase-4-dependency-audit-after-fix-1.json)

---

## 1. Scope and constraints

This slice updates only frontend package files needed for the targeted dev/test dependency fix:

- `frontend/package.json`
- `frontend/package-lock.json`

No frontend source files, backend files, Dockerfiles, workflows, migrations, `.env` files, deployment config, or provider code were changed.

Explicitly not performed:

- no `npm audit fix`;
- no `npm audit fix --force`;
- no broad `npm update`;
- no broad `npm install` without a package name;
- no Next.js runtime/framework upgrade;
- no source-code changes;
- no CI weakening;
- no Dockerfile/workflow/deployment changes;
- no production enablement;
- no provider enablement;
- no registry push or deployment.

---

## 2. Before summary

Before this slice, P4-DepAudit-Plan recorded:

| Metric | Before |
|---|---:|
| Total vulnerability records | 10 |
| Critical | 1 |
| High | 5 |
| Moderate | 4 |
| Direct vulnerable dependency records | 3 |
| Transitive vulnerable dependency records | 7 |
| Runtime dependency records | 2 |
| Dev/test/lint dependency records | 8 |

Targeted groups in this slice:

1. Vitest / Vite / vite-node / @vitest/mocker / esbuild test-tooling group.
2. eslint-config-next / @next/eslint-plugin-next / glob group only if a safe Next 14-compatible patch existed.

Inspection result:

- `vitest@3.2.6` was the smallest patched 3.x version for the critical Vitest advisory (`<3.2.6`).
- `vite@6.4.3` was the smallest available 6.x patch beyond the vulnerable Vite range (`<=6.4.2`) and uses `esbuild@^0.25.0`.
- `eslint-config-next` had no safe 14.x patch beyond the current 14.2 line; npm's reported fix path was `eslint-config-next@16.2.9`, a semver-major framework-adjacent jump, so it was not changed in this slice.
- `next` stayed at `14.2.35` and was not upgraded.

---

## 3. Package changes

| Package | Previous version | New version | Dependency type | Direct / transitive | Reason for update | Expected advisory reduction |
|---|---:|---:|---|---|---|---|
| `vitest` | `^2.1.0` in `package.json`; resolved `2.1.9` in lockfile | `^3.2.6`; resolved `3.2.6` | dev/test | Direct | Smallest patched 3.x version for critical Vitest advisory; avoids npm's force path to Vitest 4.x. | Removes critical Vitest advisory and updates Vitest test-runner chain. |
| `vite` | transitive resolved `5.4.21`; vulnerable audit range still active after Vitest bump | `^6.4.3`; resolved `6.4.3` | dev/test | Direct pin added for dev tooling | Smallest available 6.x patch above vulnerable Vite `<=6.4.2`; keeps Vite in 6.x rather than jumping to Vite 7.x. | Removes Vite advisory records and moves `esbuild` to patched `0.25.x`. |
| `@vitest/mocker` | resolved `2.1.9` | resolved `3.2.6` | dev/test | Transitive via `vitest` | Updated through Vitest. | Clears affected mocker chain. |
| `vite-node` | resolved `2.1.9` | resolved `3.2.4` | dev/test | Transitive via `vitest` | Updated through Vitest. | Clears affected vite-node chain. |
| `esbuild` | resolved `0.21.5` | resolved `0.25.12` | dev/test | Transitive via `vite` | Updated through Vite 6.4.3. | Clears esbuild dev-server advisory. |

No runtime app dependency was intentionally changed. `next` remains `14.2.35`.

---

## 4. After summary

After `vitest@3.2.6` and `vite@6.4.3`:

| Metric | After |
|---|---:|
| Total vulnerability records | 5 |
| Critical | 0 |
| High | 4 |
| Moderate | 1 |
| Runtime dependency records remaining | 2 |
| Dev/test/lint dependency records remaining | 3 |

Removed/cleared groups:

- `vitest` critical advisory;
- `@vitest/mocker` advisory record;
- `vite-node` advisory record;
- Vite advisory record;
- esbuild advisory record.

Remaining groups:

- `next` runtime advisories, with nested `postcss` finding;
- `eslint-config-next` / `@next/eslint-plugin-next` / `glob` lint-tooling chain.

---

## 5. Remaining findings

| Group | Package(s) | Severity | Why not fixed in this slice | Next slice |
|---|---|---:|---|---|
| Next.js runtime framework | `next`, nested `postcss` | High aggregate / moderate nested | User explicitly scoped P4-DepAudit-Fix-1 away from broad Next.js runtime/framework upgrade. npm's reported fix path is `next@16.2.9`, a semver-major upgrade. | P4-DepAudit-Fix-3 framework-level upgrade, or owner/security risk acceptance if staging must proceed before upgrade. |
| Next ESLint lint chain | `eslint-config-next`, `@next/eslint-plugin-next`, `glob` | High aggregate | No safe 14.x-compatible patch was available; npm's reported fix path is `eslint-config-next@16.2.9`, a semver-major framework-adjacent upgrade. | P4-DepAudit-Fix-2 if a deterministic override is approved, or P4-DepAudit-Fix-3 with framework upgrade. |

Staging/production remain blocked by these findings unless fixed or formally accepted with compensating controls.

---

## 6. Gate results

Run from `frontend/` after package updates:

| Gate | Result |
|---|---:|
| `npm ci` | PASS — install completed from lockfile; audit still reports 5 remaining vulnerabilities. |
| `npm run lint` | PASS — `next lint` reports no ESLint warnings or errors. |
| `npm run typecheck` | PASS — `tsc --noEmit` completed successfully. |
| `npm run test` | PASS — Vitest `v3.2.6`, 4 files / 141 tests passed. Expected local/mock fallback warnings appeared. |
| `npm run build` | PASS — Next.js `14.2.35` production build compiled successfully and generated 27 routes. |

No source-code changes were required.

---

## 7. Recommendation

| Question | Recommendation |
|---|---|
| Boss demo allowed? | **Allowed.** The controlled local/mock boss demo remains safe to run; dev/test critical finding is cleared. |
| Staging allowed? | **Still blocked.** Remaining Next.js runtime advisories and lint-chain findings must be fixed or explicitly accepted before externally reachable staging. Phase 4 owner/operator values are also still required. |
| Production allowed? | **Still blocked.** Production cannot proceed with unresolved high/moderate runtime findings and without Phase 4 owner/operator values. |
| Exact next dependency slice | **P4-DepAudit-Fix-2** if owner/security approves deterministic lint-chain handling; otherwise **P4-DepAudit-Fix-3** for Next.js/framework-level upgrade planning. |

Recommended next action: do not attempt a broad automatic fix. Decide whether to address the remaining lint-chain finding through a safe override/upgrade path or move directly to a controlled Next/framework upgrade slice.

---

## 8. Verification result

| Check | Result |
|---|---|
| Raw after-audit JSON validation | PASS — `phase-4-dependency-audit-after-fix-1.json` parses as valid JSON. |
| `git diff --check` | PASS — no whitespace errors. Git emitted line-ending warnings only. |
| `git status --short` | PASS — only intended files changed/added before commit. |
| Changed-file allowlist | PASS — changes limited to `frontend/package.json`, `frontend/package-lock.json`, P4-DepAudit-Fix-1 evidence files, and Phase 4 docs trackers. |
| Backend source changes | PASS — none. |
| Frontend source changes | PASS — none. |
| `.env` changes | PASS — none. |
| Dockerfile/workflow/deployment changes | PASS — none. |
| Unsafe-claim grep | PASS — only expected context was found: Phase 4 exit criteria says staging must be deployed later. No claim says production, real sending, or money movement is active. |
| Credential-pattern grep | PASS — no raw live/test key patterns found in changed docs/evidence. |
| Registry/deploy command grep | PASS — no registry push or deployment command added. |
| Package-fix scope | PASS — only targeted dev/test package updates were applied; Next.js runtime stayed `14.2.35`. |
| Safety boundary | PASS — no app source behavior, backend, auth/RBAC/RLS, billing/send gates, provider flags, production mode, AWS, deployment, registry image push, real billing, SMS, or live scraping changed. |

---

## 9. Final verdict

- P4-DepAudit-Fix-1 complete.
- Targeted dev/test dependency fixes applied.
- No app behavior changes made.
- Boss demo remains allowed.
- Staging remains blocked.
- Production remains blocked.
- No deployment, AWS provisioning, registry push, live providers, real billing, production enablement, SMS, or live scraping enabled.
