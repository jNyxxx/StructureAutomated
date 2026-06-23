export type CampaignStatus = "draft" | "researching" | "review" | "blocked" | "mock_ready";
export type GateState = "passed" | "pending" | "blocked" | "warning";

export interface CampaignRow {
  id: string;
  name: string;
  segment: string;
  status: CampaignStatus;
  selectedProspects: number;
  researchProgress: string;
  draftProgress: string;
  reviewStatus: string;
  sendGateStatus: GateState;
  followUpStatus: string;
  updatedAt: string;
  safeSummary: string;
}

export const campaignRows: CampaignRow[] = [
  {
    id: "cre-multifamily-demo",
    name: "CRE Multifamily Owner Outreach",
    segment: "CRE / Multifamily",
    status: "review",
    selectedProspects: 42,
    researchProgress: "RAG preview ready",
    draftProgress: "12 demo drafts",
    reviewStatus: "Pending human review",
    sendGateStatus: "blocked",
    followUpStatus: "Schedule preview only",
    updatedAt: "local demo",
    safeSummary: "Demo campaign for controlled review flow. No real sending enabled.",
  },
  {
    id: "industrial-investor-demo",
    name: "Industrial Investor Re-Engagement",
    segment: "CRE / Industrial",
    status: "researching",
    selectedProspects: 18,
    researchProgress: "Research queued",
    draftProgress: "Draft API pending",
    reviewStatus: "Not ready",
    sendGateStatus: "pending",
    followUpStatus: "Locked",
    updatedAt: "local demo",
    safeSummary: "Research/RAG workbench is deferred to later frontend slices.",
  },
  {
    id: "retail-suppression-demo",
    name: "Retail Portfolio Suppression Check",
    segment: "CRE / Retail",
    status: "blocked",
    selectedProspects: 9,
    researchProgress: "Blocked by compliance",
    draftProgress: "No drafts",
    reviewStatus: "Blocked",
    sendGateStatus: "blocked",
    followUpStatus: "Disabled",
    updatedAt: "local demo",
    safeSummary: "Suppression/compliance warning keeps outreach actions locked.",
  },
];

export function getCampaignById(id: string): CampaignRow | undefined {
  return campaignRows.find((campaign) => campaign.id === id);
}
