import { draftRows, type DraftRow, type GateState } from "@/components/drafts/draft-sample-data";
import type { ReviewItemDto } from "@/lib/schemas";

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
    id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
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
    safeActivity: ["Review item opened", "Send gate checked", "Backend approval API locked"],
  },
  {
    id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
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
    safeActivity: ["Unsupported claim detected", "Groundedness warning shown", "Regeneration API locked"],
  },
  {
    id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
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

function mapReviewStatus(status: string): ReviewStatus {
  const normalized = status.toLowerCase();
  if (normalized.includes("approve")) return "approved";
  if (normalized.includes("regen")) return "needs_regeneration";
  if (normalized.includes("reject") || normalized.includes("block")) return "blocked";
  return "pending_review";
}

export function getReviewItemById(id: string): ReviewItem | undefined {
  return reviewItems.find((item) => item.id === id);
}

export function reviewDtoToItem(review: ReviewItemDto, existing?: ReviewItem): ReviewItem {
  const draft = existing?.draft ?? draftRows.find((row) => row.id === review.draft_id) ?? draftRows[0];
  const reviewStatus = mapReviewStatus(review.status);
  return {
    id: review.id,
    draft,
    prospectCompany: existing?.prospectCompany ?? draft.prospectCompany,
    campaign: existing?.campaign ?? draft.campaign,
    draftSubject: draft.subject,
    reviewStatus,
    suppressionStatus: existing?.suppressionStatus ?? (draft.suppressedContact ? "suppressed" : "clear"),
    sendReadiness: "blocked",
    assignedReviewer: review.reviewer_user_id ? "backend mock reviewer" : existing?.assignedReviewer ?? "unassigned",
    updatedAt: new Date(review.updated_at).toLocaleDateString(),
    billingAccessLocked: true,
    safeActivity: [
      "Review item loaded from backend mock API",
      review.action_reason ? `Action reason: ${review.action_reason}` : "No action reason recorded",
      "Approve, reject, regeneration, and send actions locked",
    ],
  };
}

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
