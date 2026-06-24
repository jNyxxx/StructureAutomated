export type GateState = "passed" | "warning" | "missing" | "failed" | "blocked" | "pending";
export type DraftStatus = "draft_generated" | "needs_regeneration" | "blocked" | "archived" | "pending_review";

export interface EvidenceItem {
  id: string;
  title: string;
  source: string;
  trust: GateState;
  excerpt: string;
}

export interface ClaimItem {
  id: string;
  text: string;
  supported: boolean;
  reason: string;
}

export interface DraftRow {
  id: string;
  subject: string;
  prospectCompany: string;
  campaign: string;
  campaignId: string;
  status: DraftStatus;
  promptInjectionGate: GateState;
  sourceTrustGate: GateState;
  groundednessGate: GateState;
  reviewStatus: "pending_review" | "needs_regeneration" | "blocked" | "approved";
  sendGateReadiness: GateState;
  updatedAt: string;
  suppressedContact: boolean;
  body: string;
  unsupportedClaims: ClaimItem[];
  evidence: EvidenceItem[];
}

export const draftRows: DraftRow[] = [
  {
    id: "draft_demo_001",
    subject: "Grounded CRE multifamily outreach analysis",
    prospectCompany: "Northline Properties",
    campaign: "CRE Multifamily Owner Outreach",
    campaignId: "cre-multifamily-demo",
    status: "pending_review",
    promptInjectionGate: "passed",
    sourceTrustGate: "passed",
    groundednessGate: "passed",
    reviewStatus: "pending_review",
    sendGateReadiness: "passed",
    updatedAt: "2026-06-24",
    suppressedContact: false,
    body: "Hi team — based on public portfolio signals in the approved evidence set, your multifamily assets may benefit from a controlled tenant-retention outreach workflow.",
    unsupportedClaims: [],
    evidence: [
      {
        id: "ev_001",
        title: "Approved CRE portfolio signal",
        source: "Grounding Knowledge Base",
        trust: "passed",
        excerpt: "CRE portfolio signal matching user tenant acquisition criteria.",
      },
      {
        id: "ev_002",
        title: "Tenant-retention playbook",
        source: "Playbook Knowledge Base",
        trust: "passed",
        excerpt: "Grounded playbook outreach context for multifamily assets.",
      },
    ],
  },
  {
    id: "draft_demo_002",
    subject: "Industrial owner re-engagement strategy",
    prospectCompany: "Harbor Asset Group",
    campaign: "Industrial Investor Re-Engagement",
    campaignId: "industrial-investor-demo",
    status: "needs_regeneration",
    promptInjectionGate: "passed",
    sourceTrustGate: "warning",
    groundednessGate: "warning",
    reviewStatus: "needs_regeneration",
    sendGateReadiness: "passed",
    updatedAt: "2026-06-24",
    suppressedContact: false,
    body: "Hi team — this draft is currently being validated against the updated source materials. Regeneration will be triggered upon signal updates.",
    unsupportedClaims: [
      {
        id: "claim_001",
        text: "Portfolio expansion happened last quarter.",
        supported: false,
        reason: "Awaiting source verification.",
      },
    ],
    evidence: [
      {
        id: "ev_003",
        title: "Industrial market note",
        source: "Research Context",
        trust: "warning",
        excerpt: "Evidence verification in progress.",
      },
    ],
  },
  {
    id: "draft_demo_003",
    subject: "Blocked suppressed-contact draft",
    prospectCompany: "Civic Realty Partners",
    campaign: "Retail Portfolio Suppression Check",
    campaignId: "retail-suppression-demo",
    status: "blocked",
    promptInjectionGate: "missing",
    sourceTrustGate: "missing",
    groundednessGate: "missing",
    reviewStatus: "blocked",
    sendGateReadiness: "blocked",
    updatedAt: "2026-06-24",
    suppressedContact: true,
    body: "This draft is blocked because the contact is suppressed. No outreach action may proceed.",
    unsupportedClaims: [
      {
        id: "claim_002",
        text: "Suppressed contact should still receive follow-up.",
        supported: false,
        reason: "Suppression/compliance state blocks approval and sending.",
      },
    ],
    evidence: [],
  },
];

export function getDraftsByCampaignId(campaignId: string): DraftRow[] {
  return draftRows.filter((draft) => draft.campaignId === campaignId);
}

export function canApproveDraft(draft: DraftRow): boolean {
  return (
    draft.promptInjectionGate === "passed" &&
    draft.sourceTrustGate === "passed" &&
    draft.groundednessGate === "passed" &&
    draft.unsupportedClaims.length === 0 &&
    !draft.suppressedContact &&
    !["blocked", "needs_regeneration", "archived"].includes(draft.status)
  );
}
