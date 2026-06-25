import { Calculator, Lock } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { outcomeMetrics, type OutcomeMetricsView } from "./outcomes-sample-data";

export function RoiSummaryCard({ metrics = outcomeMetrics }: { metrics?: OutcomeMetricsView }) {
  return (
    <BentoCard title="ROI assumptions" description="Backend mock API/local cost and pipeline assumptions only. No Stripe, payment, CRM, ads, provider, or attribution integration." badge="Read-only">
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <Calculator className="size-4 text-blue" /> Cost assumption
          </div>
          <p className="mt-2 text-h3 text-text">{metrics.estimatedCost}</p>
          <p className="text-caption text-muted">Mock labor/tooling assumption only.</p>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <Calculator className="size-4 text-green" /> Pipeline assumption
          </div>
          <p className="mt-2 text-h3 text-text">{metrics.pipelineValue}</p>
          <p className="text-caption text-muted">Not recognized revenue.</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <GateReasonBadge state="blocked" label="No payment data" />
        <GateReasonBadge state="blocked" label="No CRM data" />
        <GateReasonBadge state="blocked" label="No real ROI" />
        <Button disabled variant="locked">
          <Lock className="size-4" /> Recalculate locked
        </Button>
      </div>
    </BentoCard>
  );
}
