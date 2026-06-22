# Frontend Guide

**Purpose:** Frontend responsibilities, hard stops, required MVP pages, review diff view, and accessibility criteria. **Frontend is UX only** — it holds no final permissions, billing truth, quota enforcement, or send authority.
**Source sections:** Master guide §18 (frontend guide).
**Status:** Draft
**Related docs:** [ARCHITECTURE](ARCHITECTURE.md) (App Router route tree §6) · [API_CONTRACT](API_CONTRACT.md) (all data via API) · [AUTH_AND_RBAC](AUTH_AND_RBAC.md) (backend enforces authz) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (review gates)

---

## 1. Frontend is UX only (hard stops)

- Frontend **never** enforces final permissions, tenant access, billing, quota, or send approval.
- All critical actions call backend APIs; **backend must reject unauthorized calls** regardless of UI state.
- Hide/disable UI for UX only — not as a security control.

## 2. Frontend rules

- Zod schemas mirror backend Pydantic schemas.
- **Never store secrets in localStorage**; prefer HttpOnly cookies for refresh tokens.
- **Never render raw AI HTML**; escape and sanitize imported/user content.
- Every form needs loading, success, validation-error, server-error, and empty states.

## 3. App Router structure

Canonical route tree → [ARCHITECTURE §6](ARCHITECTURE.md) (`(auth)/*` and `(app)/*`). Not duplicated here.

## 4. Required MVP pages

| Page | Required capabilities |
|---|---|
| Dashboard | Prospects imported, drafts generated, groundedness pass rate, review queue count, scheduled/sent, mock replies, bounce rate, booked meetings. |
| Prospects | List, filters, CSV import, validation errors, duplicate handling, detail view. |
| Campaigns | Create campaign, approval mode, follow-up settings, prospects, run status. |
| Campaign detail | Agent progress, drafts, verdicts, review status, send schedule, outcomes. |
| Review queue | Research, draft, unsupported claims, edit box, approve/reject. |
| Deliverability | Mailbox pool, warm-up status, bounce/spam/reply rates, paused inboxes. |
| Outcomes | Replies, booked meetings, ROI events, campaign performance. |
| Settings | Tenant settings, users, roles, domains, mailboxes, integrations, mock flags. |
| Billing | Subscription status, usage, checkout/portal, lock/grace messaging. |
| Audit logs | Filtered audit events for owners/admins. |

## 5. Review diff view

Layout:
- **Left:** research snippets with source links and trust labels.
- **Center:** draft subject/body with highlighted claims.
- **Right:** groundedness verdicts, unsupported claims, send-gate warnings.
- **Bottom:** approve, reject, edit, re-check.

**Approval stays disabled until the current content version passes required gates** or an explicit policy-approved hold-for-admin override exists. (Backend send gate is authoritative — see [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md).)

## 6. Accessibility (acceptance criteria)

Meet at least **WCAG AA intent**:
- [ ] Keyboard navigation + visible focus.
- [ ] Labels for all inputs.
- [ ] Non-color-only status indicators.
- [ ] Table headers present.
- [ ] Accessible toast / live regions.
- [ ] Sufficient contrast.
