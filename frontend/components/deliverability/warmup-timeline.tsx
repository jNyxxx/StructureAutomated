import { Clock3 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { warmupSteps } from "./deliverability-sample-data";

export function WarmupTimeline() {
  return (
    <BentoCard title="Warmup timeline" description="Demo warmup state machine preview only." badge="Warmup">
      <div className="space-y-3">
        {warmupSteps.map((step) => (
          <div key={step.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <Clock3 className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{step.label}</p>
                  <p className="mt-1 text-caption text-muted">{step.detail}</p>
                </div>
              </div>
              <GateReasonBadge state={step.state} />
            </div>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
