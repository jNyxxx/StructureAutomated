# ADR — Compliance Jurisdiction

**Status:** Proposed — **Owner decision needed** (must be locked before any live outbound sending; mock demos may proceed)
**Date:** 2026-06-22

## Context

This guide defines technical controls, not legal advice. SMS/TCPA, cold-outreach rules, privacy terms, DPAs, scraping/ToS, and industry claims require **counsel review before production launch**. Before any live sending, the owner must lock the target market and compliance baseline. **Mock demos can proceed without this decision; production cannot.**

## Decision

**Undecided — owner must lock the following before live sending.** Required decision fields:

- **Primary recipient market:** US CRE, Philippines, mixed/global, or another defined market.
- **Primary privacy baseline:** Philippine Data Privacy Act, CAN-SPAM, GDPR/UK GDPR, TCPA, and/or other applicable rules.
- **Allowed research sources:** public/manual/mock only, approved paid providers, customer-provided data, or other documented sources.
- **Outreach channel policy:** email-only MVP; SMS post-MVP; ads/retargeting post-MVP.
- **Sender identity:** required sender identity, unsubscribe language, business address, opt-out handling.
- **Data retention defaults:** for contacts, research snippets, embeddings, uploads, audit records, exports.

**SMS is post-MVP** — do not ship SMS sending until legal review, consent ledger, opt-out handling, quiet hours, provider registration, and compliance gates are implemented and tested.

## Options considered

| Target market | Likely baseline focus |
|---|---|
| US CRE | CAN-SPAM (+ TCPA if SMS later) |
| Philippines | Philippine Data Privacy Act |
| Mixed/global | GDPR/UK GDPR + per-market rules |
| Other defined | Per counsel |

(Listed to frame the decision; selection is the owner's.)

## Consequences

- Live sending is gated on a complete `tenant_compliance_profiles` record + legal/provider approval ([EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md)).
- **If the target market changes,** update [EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md), [PRIVACY_AND_RETENTION](../PRIVACY_AND_RETENTION.md), the send-gate tests, and owner decision records before live sending.
- Until locked, the platform stays in mock mode for outreach.

## Owner decisions / open questions

- [ ] All six required decision fields above — **owner decision needed**.
- [ ] Counsel-approved privacy/terms/outreach/unsubscribe/data-use language (launch blocker).

## Related docs

[EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md) · [PRIVACY_AND_RETENTION](../PRIVACY_AND_RETENTION.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)
