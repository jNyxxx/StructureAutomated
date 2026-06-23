import { CheckCircle2, Lock } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";

const steps = [
  "Campaign details",
  "Prospect selection",
  "Research/RAG settings",
  "Draft rules",
  "Safety/review gates",
  "Mock send/follow-up settings",
  "Review summary",
];

export function CampaignBuilderShell() {
  return (
    <div className="space-y-6">
      <BentoCard
        title="Campaign builder shell"
        description="Visual-only campaign builder. No campaign is created, persisted, or sent."
        badge="Locked"
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {steps.map((step, index) => (
            <div key={step} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-caption text-subtle">
                {index < 5 ? <CheckCircle2 className="size-4 text-blue" /> : <Lock className="size-4 text-yellow" />}
                Step {index + 1}
              </div>
              <p className="mt-1 text-small font-semibold text-text">{step}</p>
              <GateReasonBadge state={index < 5 ? "pending" : "blocked"} className="mt-3" />
            </div>
          ))}
        </div>
      </BentoCard>

      <div className="rounded-xl border border-yellow/30 bg-warnbg p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-semibold text-text">Create campaign is pending backend API</p>
            <p className="mt-2 text-small text-muted">
              This builder does not call backend APIs, persist campaign settings, start research, generate drafts, schedule follow-ups, or send messages.
            </p>
          </div>
          <GateReasonBadge state="blocked" label="Pending backend" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button disabled>
            <Lock className="size-4" /> Create campaign
          </Button>
          <Button variant="secondary" disabled>
            Save draft
          </Button>
        </div>
      </div>
    </div>
  );
}
