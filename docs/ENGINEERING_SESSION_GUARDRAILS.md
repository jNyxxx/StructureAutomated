# Engineering Session Guardrails

**Purpose:** Lightweight pre-flight and in-session rules every developer or AI agent must follow **before and during** any mutating work, so sessions start from a clean/stable tree and never silently weaken the honest local/mock posture. Supplementary process note — **not** one of the 20 implementation docs.
**Status:** Active
**Related docs:** [CLAUDE.md](../CLAUDE.md) (non-negotiable engineering rules) · [FRONTEND_GUIDE](FRONTEND_GUIDE.md) · [API_CONTRACT](API_CONTRACT.md) · [DOCUMENTATION_MANIFEST](DOCUMENTATION_MANIFEST.md)

**Why this exists:** A concurrent autonomous writer once pushed a commit that removed mock/local notices, flipped blocked gate labels to "operational", enabled non-functional actions, added fake auth, and weakened tests — then pushed it to `origin/master` during a freeze. It was reverted. These guardrails prevent a repeat.

---

## A. Pre-flight (before any implementation)

1. **Run these first, every session:**
   ```
   git status --short
   git log --oneline -8
   git remote -v
   ```
2. **Working tree must be clean before starting.** If it is dirty, inspect and classify the diffs (legitimate / formatter-only / risky / must-revert) and reconcile to clean before writing any code.
3. **Stop all other agents, file watchers, IDE auto-formatters, and concurrent sessions** before starting mutating work. Only one writer at a time.

## B. Concurrency & remote safety

4. **If `origin/master` (or local HEAD) moves unexpectedly, stop and re-audit.** Do not implement into a moving tree; identify the other writer first.
5. **Never force-push** (`--force`, `--force-with-lease`) or `reset --hard` shared history to "fix" an agent mistake. Correct mistakes with a normal `git revert` commit and a fast-forward push only.

## C. Honesty & gating (local/mock posture)

6. **Do not remove** local/mock notices, pending-backend notices, `disabled` actions, or blocked/pending gate labels **unless the real backend / API / provider is actually wired and verified.**
7. **Frontend may hide or disable only; the backend remains the source of truth** for all permissions, billing, quota, and send authority.
8. **No production-readiness claims** in code, UI, docs, or evidence without real production checks having been run.
9. **No "real Stripe / SMS / sending / live scraping / provider-connected" claims** unless that capability is actually implemented and verified — these are deferred by default.

## D. Before commit

10. **Re-run the relevant checks before committing** (e.g. frontend `lint` / `typecheck` / `test` / `build`; scoped backend tests for touched areas). Tests must genuinely assert disclosures/gates — do not weaken assertions to make a commit pass.

---

A change that violates §6–§9 must be reverted, not merged — even if it "looks cleaner." When in doubt, stop and ask the owner.
