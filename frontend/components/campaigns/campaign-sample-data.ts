import type { Campaign } from "@/lib/schemas";

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

function mapCampaignStatus(status: string): CampaignStatus {
  const normalized = status.toLowerCase();
  if (normalized.includes("block") || normalized.includes("cancel")) return "blocked";
  if (normalized.includes("review")) return "review";
  if (normalized.includes("research")) return "researching";
  if (normalized.includes("ready") || normalized.includes("mock")) return "mock_ready";
  return "draft";
}

export function campaignToRow(campaign: Campaign): CampaignRow {
  const status = mapCampaignStatus(campaign.status);
  return {
    id: campaign.id,
    name: campaign.name,
    segment: campaign.target_segment ?? "Backend mock API / segment unset",
    status,
    selectedProspects: 0,
    researchProgress: "Research actions locked",
    draftProgress: "Draft generation locked",
    reviewStatus: status === "review" ? "Pending human review" : "Read-only local/mock status",
    sendGateStatus: status === "blocked" ? "blocked" : "pending",
    followUpStatus: "Follow-up actions locked",
    updatedAt: "backend mock API",
    safeSummary: campaign.description ?? campaign.goal ?? campaign.notes ?? "Read-only campaign from backend mock API. No run, research, draft, send, or provider action is enabled.",
  };
}
