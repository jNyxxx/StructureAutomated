# P4-DepAudit-Fix-3-Plan — Framework Upgrade Approval and Migration Plan

**Purpose:** Plan the owner-approved framework upgrade needed to resolve remaining frontend dependency audit findings.
**Slice:** P4-DepAudit-Fix-3-Plan
**Date:** 2026-06-30
**Status:** Complete — docs-only plan. No package changes made.
**Base commit:** `1de5112 docs(p4): record remaining dependency audit blocker`

---

## 1. Current blocker summary

After P4-DepAudit-Fix-1 and the blocked P4-DepAudit-Fix-2 assessment, the remaining audit state is:

| Metric | Count |
|---|---:|
| Total findings | 5 |
| Critical | 0 |
| High | 4 |
| Moderate | 1 |

Remaining groups:

- Next.js runtime / nested PostCSS group.
- Next lint-chain group: `eslint-config-next`, `@next/eslint-plugin-next`, and `glob`.

Why same-major Next 14 fix is unavailable:

- Current `next` is already `14.2.35`.
- Current `eslint-config-next` is already `14.2.35`.
- `npm view next@14 version --json` and `npm view eslint-config-next@14 version --json` showed no newer 14.x release.
- The assessed fix candidates require a major-aligned framework move to Next 15.x/16.x or formal owner/security risk acceptance.

Why staging remains blocked:

- Remaining runtime findings affect the frontend framework path that would be externally reachable in staging.
- Phase 4 owner/operator values are still not locked.
- Staging should not proceed until findings are fixed or formally risk-accepted and staging values are locked.

Why production remains blocked:

- Production cannot proceed with unresolved high/moderate frontend audit findings unless there is formal owner/security risk acceptance and compensating controls.
- Production is also blocked by the wider Phase 4 owner/operator approval gates.

Why boss demo remains allowed:

- The boss demo is local/mock and controlled.
- Critical dev/test tooling findings were cleared in P4-DepAudit-Fix-1.
- No live providers, money movement, AWS infrastructure, registry image push, or production mode is enabled.

---

## 2. Candidate upgrade comparison

| Area | Next 15.5.16 path | Next 16.2.9 path |
|---|---|---|
| Package versions | `next@15.5.16`, `eslint-config-next@15.5.16`, aligned `@next/eslint-plugin-next@15.5.16` through lint config. | `next@16.2.9`, `eslint-config-next@16.2.9`, aligned `@next/eslint-plugin-next@16.2.9` through lint config. |
| Node engine | `^18.18.0 || ^19.8.0 || >=20.0.0`. Current CI/Docker use Node 20, so expected compatible. | `>=20.9.0`. Current CI/Docker use Node 20 images, but exact local/CI minor version must be confirmed before implementation. |
| ESLint compatibility | `eslint-config-next@15.5.16` supports ESLint 7/8/9. Current ESLint 8.57.x should remain compatible. | `eslint-config-next@16.2.9` requires ESLint 9+. This likely requires lint-stack migration and higher risk. |
| React compatibility | Allows React 18 and React 19 ranges. Current React 18.3.x can remain initially. | Allows React 18 and React 19 ranges. Current React 18.3.x can remain initially, but framework behavior risk is higher. |
| App Router impact | Moderate. App Router is already used; expect compatibility checks around route handlers, server/client boundaries, metadata, and build output. | Higher. Larger framework jump may include more behavioral and lint defaults. |
| Config impact | Low to moderate. Current `next.config.mjs` is simple: `reactStrictMode` and `output: standalone`. | Moderate. Same simple config helps, but version jump may expose stricter defaults or warnings. |
| Docker impact | Low. `frontend/Dockerfile.prod` already uses Node 20 Alpine and standalone output. Must rebuild image after package change. | Medium. Must confirm Node minor satisfies `>=20.9.0`; Docker image may need explicit Node tag if current image does not meet requirement. |
| CI impact | Low to moderate. CI uses Node 20, `npm ci`, lint, typecheck, build, and Docker build. | Medium to high. ESLint 9 requirement from lint config may require CI/lint changes, which are out of scope unless approved. |
| Source-code migration risk | Moderate. Possible code issues may appear in build/typecheck/lint, but React 18 compatibility lowers risk. | Higher. More likely to require source/lint/config changes. |
| Expected audit reduction | Expected to clear current Next 14 range findings if npm audit recognizes 15.5.16 as outside affected ranges. Must verify during implementation. | Expected to clear current findings, but at higher migration cost. |
| Rollback complexity | Moderate. Restore package files from previous commit and rerun frontend gates. | Higher. May involve undoing lint-stack changes and Node assumptions. |

---

## 3. Recommended path

Recommended two-step path:

1. **P4-DepAudit-Fix-3a: Next 15 controlled upgrade attempt.**
   - Target `next@15.5.16` or the latest approved 15.5.x patch.
   - Align `eslint-config-next` to the same selected 15.x version.
   - Keep React 18 initially.
   - Keep Node 20.
   - Run full frontend gates and audit evidence.
2. **P4-DepAudit-Fix-3b: Next 16 escalation only if needed.**
   - Use only if Next 15 does not clear findings or owner approves a larger jump.
   - Treat as higher-risk because lint config requires ESLint 9+ and Node minor requirements must be confirmed.

Do not choose Next 16 as the first path unless William/owner explicitly approves the larger migration and accepts the higher lint/tooling risk.

---

## 4. Required approval

William/owner approval is required before package changes.

Approval text to obtain:

```text
I approve a controlled frontend framework major upgrade attempt for AutomatedStructure.
Preferred first target: Next 15.5.16+ with aligned eslint-config-next 15.x.
The implementation may change frontend/package.json and frontend/package-lock.json only at first.
Any required frontend source, Dockerfile, workflow, or runtime behavior change must stop for approval.
A temporary break/fix window is acceptable only inside the implementation branch/session.
Rollback is required if lint, typecheck, tests, build, audit, demo login, or core demo smoke fails.
Staging remains blocked until gates pass and remaining audit findings are cleared or formally accepted.
Production remains blocked until final verification and owner/operator release values are locked.
```

---

## 5. Future implementation plan: P4-DepAudit-Fix-3-Impl

Allowed starting changes for the future implementation slice:

- update only selected framework packages first;
- keep versions explicit and aligned;
- avoid broad update commands;
- avoid unrelated dependency upgrades.

Recommended command shape for implementation after approval:

```text
cd frontend
npm install next@15.5.16 eslint-config-next@15.5.16
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
npm audit
```

Required additional checks:

- local browser demo smoke:
  - login page;
  - demo login;
  - dashboard;
  - campaign flow;
  - review queue;
  - send-gate dry run;
  - mock send intent;
  - audit/billing/compliance pages.
- frontend production Docker image build:
  - `docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:p4-depaudit-fix3 frontend`
- before/after audit evidence:
  - record pre-upgrade audit state;
  - record post-upgrade audit state;
  - document any remaining findings.

If the selected Next 15 path fails and requires source/config/Docker/CI changes, stop and report the exact blocker before modifying those files.

---

## 6. Rollback plan

Rollback procedure if implementation fails:

1. Restore `frontend/package.json` and `frontend/package-lock.json` from the previous committed state.
2. Run `npm ci` from `frontend/`.
3. Run frontend gates:
   - `npm run lint`;
   - `npm run typecheck`;
   - `npm run test`;
   - `npm run build`.
4. Confirm browser demo login still works.
5. Confirm dashboard and core local/mock flow still load.
6. Do not proceed to staging if rollback is needed.
7. Record failed candidate, failure reason, and rollback evidence.

---

## 7. Hard stop conditions

Stop the future implementation if the upgrade:

- requires an unsupported Node version;
- breaks Next build;
- breaks lint, typecheck, or tests;
- breaks demo login;
- breaks dashboard, campaign, review, send-gate, or mock-send flow;
- requires app architecture rewrite;
- requires CI weakening;
- requires Dockerfile changes not approved;
- changes auth, billing, or send-gate behavior;
- introduces new critical/high audit findings;
- touches production, deployment, provider flags, real billing, SMS, or live scraping.

---

## 8. Recommendation

| Question | Recommendation |
|---|---|
| Boss demo allowed? | Allowed. Local/mock demo remains allowed. |
| Staging allowed? | Still blocked. |
| Production allowed? | Still blocked. |
| Exact next slice | P4-DepAudit-Fix-3a: Next 15 controlled upgrade attempt, after owner approval. |
| Owner approval required? | Yes. Framework major upgrade approval is required before implementation. |

Final recommendation: approve P4-DepAudit-Fix-3a first. Escalate to Next 16 only if Next 15 fails to clear findings or William explicitly approves the larger migration.

---

## 9. Verification result

| Check | Result |
|---|---|
| `git diff --check` | PASS. |
| `git status --short` | PASS — only intended docs changed before commit. |
| Package files | PASS — no package files changed. |
| Frontend source | PASS — no frontend source changed. |
| Backend source | PASS — no backend source changed. |
| Environment files | PASS — no `.env` files changed. |
| Docker/workflow/deployment files | PASS — none changed. |
| Secret-pattern check | PASS. |
| Registry/deployment command check | PASS. |
| Safety boundary | PASS — docs-only approval plan. |

---

## 10. Final verdict

- P4-DepAudit-Fix-3-Plan complete.
- No package changes made.
- Boss demo remains allowed.
- Staging remains blocked.
- Production remains blocked.
- Implementation is still waiting for owner approval.
