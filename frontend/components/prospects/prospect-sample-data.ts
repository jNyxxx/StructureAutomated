export type SuppressionStatus = "clear" | "suppressed" | "duplicate" | "needs_review";
export type ResearchStatus = "not_started" | "queued" | "grounded" | "blocked";
export type CampaignStatus = "not_assigned" | "draft_ready" | "pending_review" | "mock_queued" | "blocked";

export interface ProspectRow {
  id: string;
  name: string;
  company: string;
  title: string;
  emailDomain: string;
  marketSegment: string;
  source: string;
  suppressionStatus: SuppressionStatus;
  researchStatus: ResearchStatus;
  campaignStatus: CampaignStatus;
  updatedAt: string;
  safeNotes: string;
}

export const prospectRows: ProspectRow[] = [
  {
    id: "prospect_demo_001",
    name: "Ava Santos",
    company: "Northline Properties",
    title: "Acquisitions Lead",
    emailDomain: "northline.example",
    marketSegment: "CRE / Multifamily",
    source: "CSV demo import",
    suppressionStatus: "clear",
    researchStatus: "grounded",
    campaignStatus: "draft_ready",
    updatedAt: "local demo",
    safeNotes: "Demo-only contact. No real email stored.",
  },
  {
    id: "prospect_demo_002",
    name: "Marco Reyes",
    company: "Harbor Asset Group",
    title: "Managing Partner",
    emailDomain: "harborassets.example",
    marketSegment: "CRE / Industrial",
    source: "CSV demo import",
    suppressionStatus: "needs_review",
    researchStatus: "queued",
    campaignStatus: "pending_review",
    updatedAt: "local demo",
    safeNotes: "Needs compliance review before outreach flow.",
  },
  {
    id: "prospect_demo_003",
    name: "Nina Cruz",
    company: "Civic Realty Partners",
    title: "Portfolio Director",
    emailDomain: "civicrealty.example",
    marketSegment: "CRE / Retail",
    source: "Manual demo row",
    suppressionStatus: "suppressed",
    researchStatus: "blocked",
    campaignStatus: "blocked",
    updatedAt: "local demo",
    safeNotes: "Suppression/compliance block. No-send state required.",
  },
  {
    id: "prospect_demo_004",
    name: "Leo Tan",
    company: "Summit Office Holdings",
    title: "Leasing Director",
    emailDomain: "summitoffice.example",
    marketSegment: "CRE / Office",
    source: "CSV demo import",
    suppressionStatus: "duplicate",
    researchStatus: "not_started",
    campaignStatus: "not_assigned",
    updatedAt: "local demo",
    safeNotes: "Duplicate marker is local/demo only.",
  },
];
