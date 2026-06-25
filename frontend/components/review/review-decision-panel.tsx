import { Lock, Pencil, RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";

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
    { label: "Billing/access", state: item.billingAccessLocked ? "blocked" : "passed" },
    { label: "Mutation actions", state: "blocked" },
    { label: "Review status", state: item.reviewStatus === "pending_review" ? "pending" : "blocked" },
  ] as const;

  return (
    <BentoCard title="Review decision" description="Human approval never bypasses safety, groundedness, suppression, billing, throttles, deliverability, or send gates. Review write actions remain disabled." badge="Decision locked">
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
            <ThumbsUp className="size-4" /> Review approval locked
          </Button>
          <Button disabled variant="secondary">
            <ThumbsDown className="size-4" /> Reject
          </Button>
          <Button disabled variant="secondary">
            <RotateCcw className="size-4" /> Request regeneration
          </Button>
          <Button disabled variant="secondary">
            <Pencil className="size-4" /> Edit draft
          </Button>
          <Button disabled variant="locked">
            <Lock className="size-4" /> Actions locked
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
