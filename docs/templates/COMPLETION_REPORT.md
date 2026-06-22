# Completion Report — <Phase / Slice>

**Phase / Slice:** <e.g. Phase 0 · Slice N — Title>
**Date:** <YYYY-MM-DD>
**Author:** <name>
**Status:** Draft | Submitted | Accepted

---

## 1. Scope

<One paragraph: what this slice/phase set out to deliver, and the explicit
boundaries (what was deliberately not built).>

## 2. Files created / updated

| File | Change | Notes |
|---|---|---|
| `path/to/file` | created / updated | <purpose> |

## 3. Migrations

| Migration | Tables / changes | Up/down verified |
|---|---|---|
| `NNNN_name` | <summary> | yes / no / n/a |

> If none: "No migrations in this slice."

## 4. Tools / commands run

```text
<command>            # <result>
```

## 5. Tests & results

| Test / gate | Result | Evidence |
|---|---|---|
| <test or gate> | pass / fail / skipped | <log/artifact link> |

## 6. Acceptance criteria

- [ ] <criterion 1>
- [ ] <criterion 2>

## 7. Security & secret confirmation

- [ ] No secrets committed (no `.env`, keys, or credentials).
- [ ] Secrets/PII not logged, audited, exported, or returned to clients.
- [ ] Tenant isolation / forced RLS not weakened (if applicable).
- [ ] Permission, billing, idempotency, rate-limit, and audit gates intact (if applicable).
- [ ] No safety gate bypassed via human approval.

## 8. Deviations from plan

<List any deviation from the accepted plan and the reason, or "None.">

## 9. Evidence bundle

<Links to logs, traces, screenshots, CI runs, test artifacts.>

## 10. Owner sign-off / go-no-go

<Owner decision, remaining accepted risks, and any follow-up items.>
