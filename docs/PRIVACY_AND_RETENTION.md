# Privacy & Retention

**Purpose:** PII handling, retention defaults, deletion/export workflows, vector/embedding purge, audit/consent retention, secret non-export rules, data rights, and privacy launch blockers. Technical controls only — not legal advice.
**Source sections:** Master guide §21 (privacy/compliance/legal), §16 (retention defaults).
**Status:** Draft (retention durations + jurisdiction = **Owner decision needed** → [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md))
**Related docs:** [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (soft-delete, `deletion_requests`, `export_requests`, embeddings) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (suppression/consent) · [CLAUDE](../CLAUDE.md) (credential/secret rules)

---

## 1. Legal position

This defines **technical controls, not legal advice.** SMS/TCPA, cold-outreach rules, privacy terms, DPAs, scraping/ToS, and industry claims require **counsel review before production launch**. Jurisdiction + baseline decision → [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md). **SMS is post-MVP** (no SMS until legal review, consent ledger, opt-out, quiet hours, provider registration, and gates are implemented and tested).

## 2. PII handling (privacy requirements)

- Maintain a **data inventory**; classify PII fields.
- Export authorized tenant/contact data.
- Delete or anonymize contact/prospect/research/embedding data when authorized, unless retention is legally required.
- Redact audit metadata.
- Encrypt data **in transit and at rest**.
- Do **not** send PII to AI/tools unless required and allowed.
- Allow **tenant-level data purge on contract end**.
- Secrets/raw credentials are **never** exported, logged, or embedded (CLAUDE rule 14 + credential-encryption rules).

## 3. Retention defaults

| Data | Default retention | Behavior |
|---|---|---|
| Contacts/prospects | While tenant active + contractual window | Exportable; deletable/anonymizable unless legal hold |
| Prospect research snippets | Campaign active + 180 days | Delete with source prospect/contact |
| Embeddings with PII | Same as source row | **Purge vector when source is deleted/anonymized** |
| Generated drafts | Campaign active + 180 days | Exportable; delete/anonymize with campaign/contact |
| Outbound messages | Retain for audit/outcome history | Redact body when content retention expires if metrics retained |
| Audit logs | **≥ 1 year, redacted** | Not deleted by normal user delete unless policy requires |
| Billing records | Accounting/legal retention | Export invoices/receipts; do not delete early |
| CSV raw files | 7 days max (unless debugging failed import) | Auto-delete |
| Import row errors | 90 days | Purge after troubleshooting window |
| Export files | 7 days | Auto-delete + revoke signed URLs |

> **Final retention durations + privacy policy language require owner/counsel approval before production.**

## 4. Deletion & export workflows

- Use **workflows, never ad-hoc SQL.** Cover user, tenant, research snippets, embeddings, uploads, and exports (`deletion_requests`, `export_requests`).
- **Soft-delete** user-facing business data by default (`deleted_at`); hard purge per retention policy / legal hold.
- **Vector/embedding purge:** when a source row is deleted or anonymized, purge its embeddings (PII embeddings share the source row's retention).
- Export produces authorized tenant/contact data; export files auto-delete after 7 days and signed URLs are revoked.
- Tenant lock/deletion invalidates access immediately ([AUTH_AND_RBAC](AUTH_AND_RBAC.md)).

## 5. Consent & suppression retention

Suppression is **append-only** and survives re-import; reinstatement is an explicit permissioned event, not deletion. Model + rules → [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md).

## 6. Privacy launch blockers

- [ ] Working **export / delete / vector-purge** workflows with policy-aligned retention.
- [ ] **Counsel-approved** privacy, terms, outreach, unsubscribe, and data-use language.
- [ ] Jurisdiction + compliance baseline locked → [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md).
- [ ] Audit redaction + ≥1-year retention enforced; secrets never in exports/logs/prompts.

## 7. Owner decisions

Final retention durations · target market + privacy baseline · allowed research sources · outreach channel policy (email-only MVP). All tracked in [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md).
