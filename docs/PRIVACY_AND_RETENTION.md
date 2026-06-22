# Privacy & Retention

**Purpose:** PII handling, retention defaults, two-stage deletion/export workflows, vector/embedding purge, audit/consent retention, secret non-export rules, data rights, and privacy launch blockers. Technical controls only - not legal advice.
**Source sections:** Master guide §21 (privacy/compliance/legal), §16 (retention defaults).
**Status:** Draft (US MVP baseline selected -> [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md))
**Related docs:** [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md) - [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (soft-delete, `deletion_requests`, `export_requests`, embeddings) - [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (suppression/consent) - [CLAUDE](../CLAUDE.md) (credential/secret rules)

---

## 1. Legal position

This defines **technical controls, not legal advice.** MVP compliance baseline is the United States. Cold outreach, privacy terms, DPAs, scraping/ToS, sender identity, unsubscribe language, and industry claims require counsel review before production launch. **SMS is post-MVP**.

## 2. PII handling

- Maintain a **data inventory**; classify PII fields.
- Export authorized tenant/contact data.
- Delete or anonymize contact/prospect/research/embedding data when authorized, unless retention is legally required.
- Redact audit metadata.
- Encrypt data **in transit and at rest**.
- Do **not** send PII to AI/tools unless required and allowed.
- Allow **tenant-level data purge on contract end**.
- Secrets/raw credentials are **never** exported, logged, prompted, embedded, or returned to clients.

## 3. Retention defaults

| Data | Default retention | Behavior |
|---|---|---|
| Contacts/prospects | While tenant active + contractual window | Exportable; deleted through two-stage workflow unless legal hold |
| Prospect research snippets | Campaign active + 180 days | Delete with source prospect/contact |
| Embeddings with PII | Same as source row | **Purge vector when source is deleted/anonymized** |
| Generated drafts | Campaign active + 180 days | Exportable; delete/anonymize with campaign/contact |
| Outbound messages | Retain for audit/outcome history | Redact body when content retention expires if metrics retained |
| Audit logs | **>= 1 year, redacted** | Not deleted by normal user delete unless policy requires |
| Billing records | Accounting/legal retention | Export invoices/receipts; do not delete early |
| CSV raw files | 7 days max (unless debugging failed import) | Auto-delete |
| Import row errors | 90 days | Purge after troubleshooting window |
| Export files | 7 days | Auto-delete + revoke signed URLs |

> Final privacy policy language requires owner/counsel approval before production.

## 4. Two-stage deletion workflow

- Use **workflows, never ad-hoc SQL.** Cover user, tenant, contacts, prospects, research snippets, embeddings, uploads, and exports.
- Soft-delete first with `deleted_at`.
- Immediately exclude deleted records from reads, sends, exports where appropriate, and agent runs.
- Schedule hard-delete after 30 days.
- GDPR/right-to-erasure requests can use a shorter required legal timeline if applicable.
- Hard-delete or anonymize linked research snippets and embeddings with the source record unless legal hold applies.
- Export files auto-delete after 7 days and signed URLs are revoked.
- Tenant lock/deletion invalidates access immediately ([AUTH_AND_RBAC](AUTH_AND_RBAC.md)).

## 5. Consent & suppression retention

Suppression is append-only and survives re-import; reinstatement is an explicit permissioned event, not deletion.

The suppression list must retain the minimum data needed to honor "never contact again", such as a hashed email plus channel/reason metadata. Do not retain raw contact data beyond what is required for suppression and legal/audit obligations.

## 6. Privacy launch blockers

- [ ] Working export / delete / vector-purge workflows with policy-aligned retention.
- [ ] Soft-delete exclusion verified for reads, sends, exports where appropriate, and agent runs.
- [ ] Scheduled 30-day hard-delete job or equivalent purge process proven.
- [ ] Counsel-approved privacy, terms, outreach, unsubscribe, and data-use language.
- [ ] Audit redaction + >=1-year retention enforced; secrets never in exports/logs/prompts.

## 7. Owner decisions

Remaining owner/counsel decisions: final privacy/terms/outreach/unsubscribe/data-use language; approved live research/scraping/paid-provider sources; any legally required shorter erasure timeline for a specific jurisdiction/request.
