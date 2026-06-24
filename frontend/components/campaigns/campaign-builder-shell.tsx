import { CheckCircle2 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";

const steps = [
  "Campaign details",
  "Prospect selection",
  "Research/RAG settings",
  "Draft rules",
  "Safety/review gates",
  "Outbound send/follow-up settings",
  "Review summary",
];

export function CampaignBuilderShell() {
  return (
    <div className="space-y-6">
      <BentoCard
        title="Campaign pipeline status"
        description="Configure tenant outreach, RAG grounding parameters, and compliance rules."
        badge="Active"
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {steps.map((step, index) => (
            <div key={step} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-caption text-subtle">
                <CheckCircle2 className="size-4 text-green" />
                Step {index + 1}
              </div>
              <p className="mt-1 text-small font-semibold text-text">{step}</p>
              <GateReasonBadge state="passed" label="Configured" className="mt-3" />
            </div>
          ))}
        </div>
      </BentoCard>

      <div className="rounded-xl border border-border bg-panel p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-semibold text-text">Campaign Configuration</p>
            <p className="mt-2 text-small text-muted">
              Ready to initialize campaign. RAG-grounded drafting, automated compliance checks, and human review steps will be configured.
            </p>
          </div>
          <GateReasonBadge state="passed" label="Ready to launch" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="default">
            Create campaign
          </Button>
          <Button variant="secondary">
            Save draft
          </Button>
        </div>
      </div>
    </div>
  );
}
