import { ArrowDown } from "lucide-react";

import { BentoCard } from "@/components/dashboard/bento-card";
import { funnelSummary } from "./outcomes-sample-data";

export function FunnelSummary({ steps = funnelSummary }: { steps?: typeof funnelSummary }) {
  return (
    <BentoCard title="Funnel summary" description="Read-only local/mock or backend mock API funnel. No CRM, attribution, Stripe, payment, or revenue integration." badge="Funnel shell">
      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={step.label}>
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-small font-semibold text-text">{step.label}</p>
                  <p className="text-caption text-muted">{step.note}</p>
                </div>
                <p className="text-h3 text-text">{step.value}</p>
              </div>
            </div>
            {index < steps.length - 1 ? <ArrowDown className="mx-auto my-2 size-4 text-subtle" /> : null}
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
