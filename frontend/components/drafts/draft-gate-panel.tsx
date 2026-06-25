import { Lock } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { canApproveDraft, type DraftRow } from "./draft-sample-data";

export function DraftGatePanel({ draft }: { draft: DraftRow }) {
  const canApprove = canApproveDraft(draft);
  const reasons = [
    { label: "Prompt injection", state: draft.promptInjectionGate },
    { label: "Source trust", state: draft.sourceTrustGate },
    { label: "Groundedness", state: draft.groundednessGate },
    { label: "Unsupported claims", state: draft.unsupportedClaims.length === 0 ? "passed" : "blocked" },
    { label: "Suppression", state: draft.suppressedContact ? "blocked" : "passed" },
    { label: "Write actions", state: "blocked" },
  ] as const;

  return (
    <BentoCard title="Draft review gates" description="Generate, review, and send actions remain disabled in this read-only frontend slice." badge="Approval locked">
      <div className="space-y-3">
        {reasons.map((reason) => (
          <div key={reason.label} className="flex items-center justify-between gap-3 rounded-medium border border-border bg-panel2 p-3">
            <p className="text-small font-semibold text-text">{reason.label}</p>
            <GateReasonBadge state={reason.state} />
          </div>
        ))}
        <div className="flex flex-wrap gap-2 pt-2">
          <Button disabled={!canApprove}>
            <Lock className="size-4" /> Approve draft
          </Button>
          <Button disabled variant="secondary">
            Regenerate
          </Button>
          <Button disabled variant="locked">
            Send locked
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
