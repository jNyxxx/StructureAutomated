# ADR - Compliance Jurisdiction

**Status:** Accepted - United States MVP baseline
**Date:** 2026-06-22

## Context

This guide defines technical controls, not legal advice. Cold outreach, privacy terms, DPAs, scraping/ToS, sender identity, unsubscribe language, and industry claims still require counsel review before production launch.

## Decision

The MVP compliance baseline is the **United States**, and the first target market is the **US**.

Phase 1 cold outreach should follow US email outreach compliance assumptions. SMS remains post-MVP. Live sending remains gated behind compliance review and owner approval.

For the first real client, every AI-generated cold-email draft requires manual human approval, even after prompt-injection, groundedness, compliance, and send gates pass. Auto-send can be added later only as a per-tenant/per-campaign configuration and must still require every safety gate to pass.

## Options considered

| Target market | Verdict |
|---|---|
| United States | Accepted for MVP and first target market |
| Philippines | Deferred |
| Mixed/global | Deferred until counsel-approved per-market rules exist |
| Other defined market | Deferred |

## Consequences

- `tenant_compliance_profiles` remains required before live sending.
- Live sending requires legal/provider review and explicit owner approval.
- SMS cannot ship until a later phase implements consent ledger, opt-out handling, quiet hours, provider registration, and SMS-specific gates.
- If the target market changes, update [EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md), [PRIVACY_AND_RETENTION](../PRIVACY_AND_RETENTION.md), send-gate tests, and owner decision records before live sending.

## Owner decisions / open questions

- [x] MVP compliance baseline selected: United States.
- [x] First target market selected: US.
- [x] SMS remains post-MVP.
- [x] First real client requires manual approval for every AI-generated cold-email draft.
- [ ] Counsel-approved privacy/terms/outreach/unsubscribe/data-use language remains required before live sending.
- [ ] Approved live research/scraping/paid-provider sources remain required before live research.

## Related docs

[EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md) - [PRIVACY_AND_RETENTION](../PRIVACY_AND_RETENTION.md) - [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)
