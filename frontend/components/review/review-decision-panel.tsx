import { Pencil, RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { canApproveReviewItem, type ReviewItem } from "./review-sample-data";

export function ReviewDecisionPanel({ item }: { item: ReviewItem }) {
  const canApprove = canApproveReviewItem(item);
  const blockers = [
    { label: "Prompt injection", state: item.draft.promptInjectionGate },
    { label: "Source trust", state: item.draft.sourceTrustGate },
    { label: "Groundedness", state: item.draft.groundednessGate },
    { label: "Unsupported claims", state: item.draft.unsupportedClaims.length === 0 ? "passed" : "blocked" },
    { label: "Suppression", state: item.suppressionStatus === "clear" ? "passed" : "blocked" },
    { label: "Review status", state: item.reviewStatus === "pending_review" ? "passed" : "passed" },
  ] as const;

  return (
    <BentoCard title="Review decision" description="Human approval reviews safety, groundedness, suppression, throttles, and deliverability gates before queue release." badge="Active">
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          {blockers.map((blocker) => (
            <div key={blocker.label} className="flex items-center justify-between gap-3 rounded-medium border border-border bg-panel2 p-3">
              <p className="text-small font-semibold text-text">{blocker.label}</p>
              <GateReasonBadge state={blocker.state} />
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 pt-2">
          <Button disabled={!canApprove}>
            <ThumbsUp className="size-4" /> Approve
          </Button>
          <Button variant="secondary">
            <ThumbsDown className="size-4" /> Reject
          </Button>
          <Button variant="secondary">
            <RotateCcw className="size-4" /> Request regeneration
          </Button>
          <Button variant="secondary">
            <Pencil className="size-4" /> Edit draft
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
