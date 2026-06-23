import { draftRows, type DraftRow, type GateState } from "@/components/drafts/draft-sample-data";

export type ReviewStatus = "pending_review" | "needs_regeneration" | "blocked" | "approved";
export type SuppressionStatus = "clear" | "suppressed" | "needs_review";

export interface ReviewItem {
  id: string;
  draft: DraftRow;
  prospectCompany: string;
  campaign: string;
  draftSubject: string;
  reviewStatus: ReviewStatus;
  suppressionStatus: SuppressionStatus;
  sendReadiness: GateState;
  assignedReviewer: string;
  updatedAt: string;
  billingAccessLocked: boolean;
  safeActivity: string[];
}

export const reviewItems: ReviewItem[] = [
  {
    id: "review_demo_001",
    draft: draftRows[0],
    prospectCompany: draftRows[0].prospectCompany,
    campaign: draftRows[0].campaign,
    draftSubject: draftRows[0].subject,
    reviewStatus: "pending_review",
    suppressionStatus: "clear",
    sendReadiness: "blocked",
    assignedReviewer: "owner@example.com",
    updatedAt: "local demo",
    billingAccessLocked: true,
    safeActivity: ["Review item opened", "Send gate checked", "Backend approval API pending"],
  },
  {
    id: "review_demo_002",
    draft: draftRows[1],
    prospectCompany: draftRows[1].prospectCompany,
    campaign: draftRows[1].campaign,
    draftSubject: draftRows[1].subject,
    reviewStatus: "needs_regeneration",
    suppressionStatus: "needs_review",
    sendReadiness: "blocked",
    assignedReviewer: "owner@example.com",
    updatedAt: "local demo",
    billingAccessLocked: true,
    safeActivity: ["Unsupported claim detected", "Groundedness warning shown", "Regeneration API pending"],
  },
  {
    id: "review_demo_003",
    draft: draftRows[2],
    prospectCompany: draftRows[2].prospectCompany,
    campaign: draftRows[2].campaign,
    draftSubject: draftRows[2].subject,
    reviewStatus: "blocked",
    suppressionStatus: "suppressed",
    sendReadiness: "blocked",
    assignedReviewer: "compliance@example.com",
    updatedAt: "local demo",
    billingAccessLocked: true,
    safeActivity: ["Suppression state detected", "Approval blocked", "No-send state enforced"],
  },
];

export function canApproveReviewItem(item: ReviewItem): boolean {
  return (
    item.draft.promptInjectionGate === "passed" &&
    item.draft.sourceTrustGate === "passed" &&
    item.draft.groundednessGate === "passed" &&
    item.draft.unsupportedClaims.length === 0 &&
    item.suppressionStatus === "clear" &&
    !["blocked", "needs_regeneration", "archived"].includes(item.draft.status) &&
    !item.billingAccessLocked &&
    item.reviewStatus === "pending_review" &&
    false
  );
}
