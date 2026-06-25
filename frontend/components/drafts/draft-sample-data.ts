import type { Draft, DraftEvidence } from "@/lib/schemas";

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
    id: "66666666-6666-6666-6666-666666666666",
    subject: "Demo: reduce vacancy risk with grounded outreach",
    prospectCompany: "Northline Properties",
    campaign: "CRE Multifamily Owner Outreach",
    campaignId: "cre-multifamily-demo",
    status: "pending_review",
    promptInjectionGate: "passed",
    sourceTrustGate: "passed",
    groundednessGate: "passed",
    reviewStatus: "pending_review",
    sendGateReadiness: "blocked",
    updatedAt: "local demo",
    suppressedContact: false,
    body: "Hi team — based on public portfolio signals in the approved evidence set, your multifamily assets may benefit from a controlled tenant-retention outreach workflow. This is a demo draft and cannot be sent.",
    unsupportedClaims: [],
    evidence: [
      {
        id: "77777777-7777-7777-7777-777777777777",
        title: "Approved CRE portfolio signal",
        source: "local knowledge chunk",
        trust: "passed",
        excerpt: "Local/demo evidence card. No live scraping or provider enrichment was used.",
      },
      {
        id: "88888888-8888-8888-8888-888888888888",
        title: "Tenant-retention playbook",
        source: "local RAG sample",
        trust: "passed",
        excerpt: "Grounded sample context for safe frontend review only.",
      },
    ],
  },
  {
    id: "99999999-9999-9999-9999-999999999999",
    subject: "Demo: industrial owner re-engagement angle",
    prospectCompany: "Harbor Asset Group",
    campaign: "Industrial Investor Re-Engagement",
    campaignId: "industrial-investor-demo",
    status: "needs_regeneration",
    promptInjectionGate: "passed",
    sourceTrustGate: "warning",
    groundednessGate: "warning",
    reviewStatus: "needs_regeneration",
    sendGateReadiness: "blocked",
    updatedAt: "local demo",
    suppressedContact: false,
    body: "Hi team — this draft contains a claim that needs stronger evidence before review can continue. Regeneration is locked until backend APIs exist.",
    unsupportedClaims: [
      {
        id: "claim_001",
        text: "Portfolio expansion happened last quarter.",
        supported: false,
        reason: "Unsupported by local/demo evidence.",
      },
    ],
    evidence: [
      {
        id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        title: "Industrial market note",
        source: "local sample chunk",
        trust: "warning",
        excerpt: "Evidence is incomplete and requires backend validation.",
      },
    ],
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    subject: "Demo: blocked suppressed-contact draft",
    prospectCompany: "Civic Realty Partners",
    campaign: "Retail Portfolio Suppression Check",
    campaignId: "retail-suppression-demo",
    status: "blocked",
    promptInjectionGate: "missing",
    sourceTrustGate: "missing",
    groundednessGate: "missing",
    reviewStatus: "blocked",
    sendGateReadiness: "blocked",
    updatedAt: "local demo",
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

export function getDraftById(id: string): DraftRow | undefined {
  return draftRows.find((draft) => draft.id === id);
}

function mapDraftStatus(status: string): DraftStatus {
  const normalized = status.toLowerCase();
  if (normalized.includes("block")) return "blocked";
  if (normalized.includes("regen")) return "needs_regeneration";
  if (normalized.includes("archive")) return "archived";
  if (normalized.includes("review")) return "pending_review";
  return "draft_generated";
}

export function evidenceToItem(evidence: DraftEvidence): EvidenceItem {
  return {
    id: evidence.id,
    title: `${evidence.source_type} evidence`,
    source: `backend mock API source ${evidence.source_id}`,
    trust: "passed",
    excerpt: evidence.content_snippet,
  };
}

export function draftToRow(draft: Draft, existing?: DraftRow, evidence: EvidenceItem[] = existing?.evidence ?? []): DraftRow {
  const status = mapDraftStatus(draft.status);
  return {
    id: draft.id,
    subject: draft.subject,
    prospectCompany: existing?.prospectCompany ?? "Backend mock contact",
    campaign: existing?.campaign ?? "Backend mock campaign",
    campaignId: draft.campaign_id,
    status,
    promptInjectionGate: existing?.promptInjectionGate ?? "passed",
    sourceTrustGate: evidence.length > 0 ? "passed" : "pending",
    groundednessGate: evidence.length > 0 ? "passed" : "pending",
    reviewStatus: status === "blocked" ? "blocked" : status === "needs_regeneration" ? "needs_regeneration" : "pending_review",
    sendGateReadiness: "blocked",
    updatedAt: new Date(draft.updated_at).toLocaleDateString(),
    suppressedContact: existing?.suppressedContact ?? false,
    body: draft.body,
    unsupportedClaims: existing?.unsupportedClaims ?? [],
    evidence,
  };
}

export function canApproveDraft(draft: DraftRow): boolean {
  return (
    draft.promptInjectionGate === "passed" &&
    draft.sourceTrustGate === "passed" &&
    draft.groundednessGate === "passed" &&
    draft.unsupportedClaims.length === 0 &&
    !draft.suppressedContact &&
    !["blocked", "needs_regeneration", "archived"].includes(draft.status) &&
    false
  );
}
