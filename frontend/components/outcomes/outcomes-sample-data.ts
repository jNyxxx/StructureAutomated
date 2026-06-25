import type { OutcomesSummary, RoiSummary } from "@/lib/schemas";

export const DEFAULT_ROI_CAMPAIGN_ID = "44444444-4444-4444-4444-444444444444";

export interface RoiTrendPoint {
  label: string;
  pipelineValue: number;
  demoCost: number;
  replies: number;
}

export interface OutcomeMetricsView {
  mockSent: number;
  replies: number;
  positiveReplies: number;
  meetings: number;
  opportunities: number;
  won: number;
  lost: number;
  unsubscribes: number;
  bounces: number;
  complaints: number;
  pipelineValue: string;
  estimatedCost: string;
  estimatedRoi: string;
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

export const outcomeMetrics: OutcomeMetricsView = {
  mockSent: 18,
  replies: 5,
  positiveReplies: 3,
  meetings: 2,
  opportunities: 1,
  won: 0,
  lost: 0,
  unsubscribes: 1,
  bounces: 1,
  complaints: 0,
  pipelineValue: "$42k demo",
  estimatedCost: "$480 demo",
  estimatedRoi: "preview only",
};

export const funnelSummary = [
  { label: "Prospects selected", value: 69, note: "read-only local/mock prospects" },
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
    id: "44444444-4444-4444-4444-444444444444",
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
    id: "55555555-5555-5555-5555-555555555555",
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
    id: "66666666-6666-6666-6666-666666666666",
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

function formatMoney(cents: number, suffix = " mock"): string {
  const dollars = Math.round(cents / 100);
  return `$${dollars.toLocaleString()}${suffix}`;
}

export function outcomesToMetrics(outcomes: OutcomesSummary, roi?: RoiSummary | null): OutcomeMetricsView {
  return {
    mockSent: roi?.sent_count ?? outcomeMetrics.mockSent,
    replies: outcomes.reply_count,
    positiveReplies: outcomes.positive_reply_count,
    meetings: outcomes.meeting_booked_count,
    opportunities: outcomes.opportunity_count,
    won: outcomes.deal_won_count,
    lost: outcomes.deal_lost_count,
    unsubscribes: outcomes.unsubscribe_count,
    bounces: outcomes.bounce_count,
    complaints: outcomes.complaint_count,
    pipelineValue: roi ? formatMoney(roi.estimated_pipeline_value_cents, " mock") : outcomeMetrics.pipelineValue,
    estimatedCost: roi ? formatMoney(roi.estimated_cost_cents, " mock") : outcomeMetrics.estimatedCost,
    estimatedRoi: roi?.estimated_roi_percent == null ? "preview only" : `${roi.estimated_roi_percent.toFixed(1)}% mock`,
  };
}

export function outcomesToFunnel(outcomes: OutcomesSummary, sentCount: number) {
  return [
    { label: "Mock sends", value: sentCount, note: "backend mock API count only" },
    { label: "Replies", value: outcomes.reply_count, note: "read-only local/mock outcomes" },
    { label: "Positive replies", value: outcomes.positive_reply_count, note: "not live CRM attribution" },
    { label: "Meetings", value: outcomes.meeting_booked_count, note: "mock/local outcome events" },
    { label: "Opportunities", value: outcomes.opportunity_count, note: "no CRM/provider sync" },
  ];
}

export function outcomesToRows(outcomes: OutcomesSummary, roi?: RoiSummary | null): CampaignOutcomeRow[] {
  const row = campaignOutcomeRows[0];
  return [
    {
      ...row,
      id: roi?.campaign_id ?? outcomes.campaign_id ?? row.id,
      mockSent: roi?.sent_count ?? row.mockSent,
      replies: outcomes.reply_count,
      meetings: outcomes.meeting_booked_count,
      opportunities: outcomes.opportunity_count,
      pipelineValue: roi ? formatMoney(roi.estimated_pipeline_value_cents, " mock") : row.pipelineValue,
      roiStatus: "preview",
      updatedAt: "backend mock API",
    },
  ];
}

export function roiToTrend(roi?: RoiSummary | null, replies = outcomeMetrics.replies): RoiTrendPoint[] {
  if (!roi) return roiTrend;
  return [
    { label: "Sent", pipelineValue: 0, demoCost: roi.estimated_cost_cents / 100, replies: roi.sent_count },
    { label: "Pipeline", pipelineValue: roi.estimated_pipeline_value_cents / 100, demoCost: roi.estimated_cost_cents / 100, replies },
    { label: "Won", pipelineValue: roi.estimated_won_value_cents / 100, demoCost: roi.estimated_cost_cents / 100, replies },
  ];
}
