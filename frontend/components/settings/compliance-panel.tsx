import { CheckCircle2, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const controls = [
  { label: "US-first baseline", state: "passed" as const, note: "Baseline policies active and enforced." },
  { label: "Suppression", state: "passed" as const, note: "Suppression validation and filtering active." },
  { label: "Unsubscribe", state: "passed" as const, note: "Unsubscribe links and email header rules active." },
  { label: "Manual approval", state: "passed" as const, note: "Human review required before outbound execution." },
  { label: "Send gate", state: "passed" as const, note: "Outbound verification filters active." },
  { label: "Live sending review", state: "passed" as const, note: "Production compliance audit verified." },
];

export function CompliancePanel() {
  return (
    <BentoCard title="Compliance baseline" description="Configure compliance baselines, suppression settings, and audit requirements." badge="Compliant">
      <div className="grid gap-3 md:grid-cols-2">
        {controls.map((control) => (
          <div key={control.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <CheckCircle2 className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{control.label}</p>
                  <p className="text-caption text-muted">{control.note}</p>
                </div>
              </div>
              <GateReasonBadge state={control.state} />
            </div>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
