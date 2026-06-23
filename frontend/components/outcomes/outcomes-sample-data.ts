export interface RoiTrendPoint {
  label: string;
  pipelineValue: number;
  demoCost: number;
  replies: number;
}

export interface CampaignOutcomeRow {
  id: string;
  campaign: string;
  segment: string;
  mockSent: number;
  replies: number;
  meetings: number;
  opportunities: number;
  pipelineValue: string;
  roiStatus: "preview" | "blocked" | "pending";
  updatedAt: string;
}

export const outcomeMetrics = {
  mockSent: 18,
  replies: 5,
  meetings: 2,
  opportunities: 1,
  pipelineValue: "$42k demo",
  estimatedCost: "$480 demo",
};

export const funnelSummary = [
  { label: "Prospects selected", value: 69, note: "local/demo prospects" },
  { label: "Drafts reviewed", value: 12, note: "human review preview" },
  { label: "Mock sends", value: 18, note: "no provider call" },
  { label: "Replies", value: 5, note: "sample outcome rows" },
  { label: "Meetings", value: 2, note: "demo assumption" },
];

export const roiTrend: RoiTrendPoint[] = [
  { label: "Week 1", pipelineValue: 8000, demoCost: 160, replies: 1 },
  { label: "Week 2", pipelineValue: 12000, demoCost: 240, replies: 2 },
  { label: "Week 3", pipelineValue: 22000, demoCost: 360, replies: 4 },
  { label: "Week 4", pipelineValue: 42000, demoCost: 480, replies: 5 },
];

export const campaignOutcomeRows: CampaignOutcomeRow[] = [
  {
    id: "outcome_demo_001",
    campaign: "CRE Multifamily Owner Outreach",
    segment: "CRE / Multifamily",
    mockSent: 12,
    replies: 4,
    meetings: 2,
    opportunities: 1,
    pipelineValue: "$42k demo",
    roiStatus: "preview",
    updatedAt: "local demo",
  },
  {
    id: "outcome_demo_002",
    campaign: "Industrial Investor Re-Engagement",
    segment: "CRE / Industrial",
    mockSent: 6,
    replies: 1,
    meetings: 0,
    opportunities: 0,
    pipelineValue: "$0 demo",
    roiStatus: "pending",
    updatedAt: "local demo",
  },
  {
    id: "outcome_demo_003",
    campaign: "Retail Portfolio Suppression Check",
    segment: "CRE / Retail",
    mockSent: 0,
    replies: 0,
    meetings: 0,
    opportunities: 0,
    pipelineValue: "$0 blocked",
    roiStatus: "blocked",
    updatedAt: "local demo",
  },
];
