# P4-DepAudit-Plan — Dependency Audit Triage Plan

**Purpose:** Triage frontend npm audit findings before any package update, lockfile change, or automatic audit fix.
**Slice:** P4-DepAudit-Plan
**Date:** 2026-06-30
**Status:** Complete — docs-only triage plan. No package changes, no `npm audit fix`, no installs, no deployment, no AWS provisioning, no registry push, no live providers, no real billing, no production enablement.
**Base commit:** `186e873 docs(p4): add demo walkthrough script`
**Raw audit evidence:** [phase-4-dependency-audit-raw.json](phase-4-dependency-audit-raw.json)

---

## 1. Scope and constraints

This slice only records the dependency audit result and a safe fix plan. It does not update dependencies.

Explicitly not performed:

- no `npm audit fix`;
- no `npm audit fix --force`;
- no `npm update`;
- no `npm install`;
- no `npm dedupe`;
- no package version edits;
- no `package.json` or `package-lock.json` edits;
- no deployment, AWS provisioning, registry push, live providers, real billing, production enablement, SMS, or live scraping.

---

## 2. Commands run

Run from `D:\AutomatedStructure` and `D:\AutomatedStructure\frontend`:

```text
git fetch origin
git status --short
git log --oneline -20
git ls-remote origin refs/heads/master
git rev-parse HEAD
git rev-parse origin/master
find .git -name "*.lock" -print
npm audit --json
npm audit
```

`npm outdated` was not used for the final evidence because the required triage data was already present in `npm audit --json`, and this slice must avoid package mutation or automatic resolution.

---

## 3. Audit summary

Raw audit file: `docs/evidence/phase-4-dependency-audit-raw.json`.

| Metric | Result |
|---|---:|
| Total vulnerability records | 10 |
| Critical | 1 |
| High | 5 |
| Moderate | 4 |
| Low / info | 0 |
| Direct vulnerable dependency records | 3 |
| Transitive vulnerable dependency records | 7 |
| Production/runtime dependency records | 2 |
| Dev/test/lint dependency records | 8 |
| Total lockfile dependencies reported by npm audit | 681 |
| Production dependencies reported by npm audit | 182 |
| Dev dependencies reported by npm audit | 490 |

Direct vulnerable records:

- `next` — production dependency.
- `eslint-config-next` — dev/lint dependency.
- `vitest` — dev/test dependency.

Transitive vulnerable records:

- `postcss` under `next`.
- `@next/eslint-plugin-next` and `glob` under `eslint-config-next`.
- `@vitest/mocker`, `vite`, `vite-node`, and `esbuild` under `vitest`.

npm reported force-fix paths that jump to major versions:

- `next@16.2.9` for Next.js/PostCSS findings.
- `eslint-config-next@16.2.9` for ESLint/Glob findings.
- `vitest@4.1.9` for Vitest/Vite/esbuild findings.

These force-fix paths are treated as unsafe for automatic application because they are semver-major and may break Next.js 14.2.x compatibility, lint behavior, test behavior, or production builds.

---

## 4. Risk classification

| Group | Package(s) | Severity | Direct / transitive | Affected dependency path | Exploit relevance to this app | Production runtime impact | Demo/local-only impact | Recommended action | Blocks boss demo? | Blocks staging? | Blocks production? |
|---|---|---:|---|---|---|---|---|---|---:|---:|---:|
| Next.js runtime advisories | `next` | High aggregate | Direct | `frontend/package.json` → `next` | Relevant once the Next app is exposed beyond local demo. Advisories include DoS, SSRF, cache poisoning, request smuggling, middleware/proxy, image optimizer, and App Router/RSC concerns. | High: this is the frontend runtime/framework. Must be fixed or explicitly risk-accepted before external staging/prod. | Low for controlled localhost boss demo with trusted operator and no public exposure. | Prefer targeted Next 14-compatible patch first if available. Preserve 14.2.35 compatibility unless deliberate framework upgrade is approved. | No | Yes | Yes |
| Next.js nested PostCSS | `postcss` under `next` | Moderate | Transitive | `next` → bundled/nested `postcss` | Relevant if vulnerable CSS stringify path is reachable through framework/build/runtime behavior. | Medium: tied to framework version; fix likely comes through Next patch/upgrade. | Low for local controlled demo. | Resolve with Next framework patch/upgrade path; do not override blindly without build validation. | No | Yes | Yes |
| ESLint config / plugin chain | `eslint-config-next`, `@next/eslint-plugin-next`, `glob` | High aggregate | Direct + transitive | `eslint-config-next` → `@next/eslint-plugin-next` → `glob` | Mostly CI/developer lint-time exposure. `glob` advisory involves command execution through CLI `-c/--cmd`; risk depends on untrusted glob input or direct CLI use. | Low direct runtime impact if not included in production image/runtime. Still affects CI trust and dependency hygiene. | Low for browser demo; not part of user-facing runtime. | Try safe `eslint-config-next` 14.2.x-compatible patch first. Avoid semver-major Next 16 lint config unless planned. Run lint/typecheck/tests/build after change. | No | Medium | Medium |
| Vitest UI / test runner | `vitest` | Critical | Direct | `frontend/package.json` → `vitest` | Critical advisory applies when Vitest UI server is listening. Current scripts use `vitest run`, not a long-running UI server. | Low direct production runtime impact if dev dependencies are excluded from production runtime image. CI/dev risk remains. | Low for boss demo if no Vitest UI server is exposed. | Prioritize as first dev-dependency fix. Prefer minimal compatible upgrade that clears advisory; if only major is available, plan focused test-runner migration. | No | Medium | Medium |
| Vite chain under Vitest | `vite`, `vite-node`, `@vitest/mocker`, `esbuild` | High/moderate aggregate | Transitive | `vitest` → `vite` / `vite-node` / `@vitest/mocker` → `esbuild` | Relevant to dev server/test tooling. Vite advisories include path traversal and Windows path issues; esbuild advisory affects dev server request exposure. | Low direct runtime impact if not shipped in production runtime. CI/dev exposure matters. | Low for boss demo if dev/test servers are not exposed. | Resolve through Vitest/Vite compatible upgrade group. Do not run Vite/Vitest servers on public interfaces. | No | Medium | Medium |

Legend:

- **Blocks boss demo:** whether the controlled local/mock walkthrough is blocked.
- **Blocks staging:** whether unresolved findings block external staging or require explicit owner/security risk acceptance.
- **Blocks production:** whether unresolved findings block public production launch.

---

## 5. Fix strategy

Rules for future fix slices:

1. Do not run automatic fixes.
2. Do not use `npm audit fix --force`.
3. Prefer minimal targeted upgrades over broad upgrades.
4. Preserve Next.js 14.2.35 compatibility unless a deliberate framework upgrade is approved.
5. Do not break lockfile determinism: update `package.json` and `package-lock.json` together only in approved fix slices.
6. Update one dependency group at a time.
7. After each dependency group fix, run full frontend gates:
   - `npm ci`
   - `npm run lint`
   - `npm run typecheck`
   - `npm run test`
   - `npm run build`
8. Run backend gates if shared tooling, Docker behavior, CI, or repo-level scripts change.
9. Rebuild production Docker images after package changes:
   - backend production image if backend/shared workflow changed;
   - frontend production image after any frontend package change.
10. Confirm the local/mock demo login still works after any frontend package or framework update.
11. Confirm auth, billing, send-gate, mock-send, and audit UI flows still behave the same.
12. Re-run `npm audit --json` and record a new raw evidence file after each fix slice.

Do not accept a fix that weakens CI, auth, billing gates, send gates, tenant isolation, boot guard, or demo safety labels.

---

## 6. Proposed future slices

| Slice | Purpose | Allowed changes | Required gates |
|---|---|---|---|
| P4-DepAudit-Fix-1 | Safe dev dependency fixes | Target `vitest`/Vite chain and/or `eslint-config-next` only if a minimal compatible upgrade exists. | Frontend `npm ci`, lint, typecheck, tests, build; local demo login smoke; audit evidence. |
| P4-DepAudit-Fix-2 | Safe transitive dependency fixes | Target transitive overrides only if low-risk and deterministic; avoid fragile overrides without evidence. | Same frontend gates; inspect lockfile diff carefully; Docker frontend build. |
| P4-DepAudit-Fix-3 | Framework-level upgrade if required | Next.js framework upgrade only if 14.2.x patch cannot clear runtime advisories or security owner approves larger upgrade. | Full frontend gates, backend gates if CI/shared workflow changes, production Docker builds, local/mock browser smoke. |
| P4-DepAudit-Verify | Full verification closeout | No new packages unless required by the approved fix path. | Re-run npm audit, CI-equivalent frontend gates, Docker builds, demo walkthrough smoke, updated evidence/manifest/runbook. |

Recommended order: start with dev/test/lint fixes if a safe non-breaking path exists, then assess Next.js runtime advisories. If the only Next.js fix path is major, treat it as a separate owner-approved framework upgrade.

---

## 7. Hard stop conditions

Stop immediately if any future dependency fix:

- requires a major framework upgrade without owner/security approval;
- breaks `next build`;
- breaks demo login or local/mock auth behavior;
- breaks dashboard/campaign/review/send-gate/mock-send flow;
- breaks production Docker build;
- introduces a package with unknown license or security risk;
- requires weakening CI, lint, typecheck, tests, or Docker validation;
- changes runtime behavior near auth, billing gates, send gates, tenant context, or audit;
- alters `.env`, secrets, deployment config, provider flags, or production mode;
- attempts registry push, deployment, AWS provisioning, live email, Stripe money movement, SMS, or live scraping.

---

## 8. Recommendation

| Question | Recommendation |
|---|---|
| Do findings block the boss demo? | **No**, not for controlled local/mock review, as long as no dev/test servers are exposed publicly and no live providers are enabled. |
| Do findings block staging? | **Yes, or require explicit owner/security risk acceptance.** Next.js runtime findings are relevant to any externally reachable staging frontend. Dev/test/lint findings should also be cleaned or accepted before trusted staging CI/release evidence. |
| Do findings block production? | **Yes.** Public production should not launch with unresolved high/critical audit findings unless a signed risk acceptance and compensating controls exist. |
| Exact next fix slice | **P4-DepAudit-Fix-1** if a safe targeted dev dependency patch exists; otherwise prepare owner decision for P4-DepAudit-Fix-3 framework-level upgrade. |

Short recommendation for William:

> The demo can proceed. Before staging or production, we should fix or formally accept the dependency audit findings. Do not run automatic fixes; the npm-suggested path jumps to major versions and could break the frontend. The safest next step is a controlled dependency-fix slice, one group at a time, with full frontend gates and Docker verification after each change.

---

## 9. Verification result

| Check | Result |
|---|---|
| Raw audit JSON validation | PASS — `phase-4-dependency-audit-raw.json` parses as valid JSON. |
| `git diff --check` | PASS — no whitespace errors. Git emitted line-ending warnings only. |
| `git status --short` | PASS — only intended docs/evidence files are changed/added. |
| `package.json` changes | PASS — no `frontend/package.json` changes. |
| `package-lock.json` changes | PASS — no `frontend/package-lock.json` changes. |
| `node_modules` staged changes | PASS — none staged or tracked. |
| Changed-file scope | PASS — no backend, frontend source, app config, migration, `.env`, Dockerfile, workflow, package, or test files changed. |
| Unsafe-claim grep | PASS — only expected context was found: Phase 4 exit criteria says staging must be deployed later. No claim says production, real sending, or money movement is active. |
| Credential-pattern grep | PASS — no raw live/test key patterns found in changed docs/evidence. |
| Registry/deploy command grep | PASS — no registry push or deployment command added. |
| Provider SDK/API calls | PASS by scope — docs/evidence-only changes; no code or package files changed. |
| Safety boundary | PASS — P4-DepAudit-Plan records triage only. No automatic fixes, package updates, lockfile edits, installs, AWS provisioning, deployment, image push, live provider enablement, real billing, production enablement, SMS, or live scraping. |

---

## 10. Final verdict

- P4-DepAudit-Plan created.
- Raw npm audit JSON evidence recorded.
- No package updates or lockfile changes made.
- Boss demo remains allowed.
- Staging and production remain blocked until findings are fixed or explicitly accepted, and until Phase 4 owner/operator values are locked.
- No deployment, AWS provisioning, registry push, live providers, real billing, production enablement, SMS, or live scraping enabled.
