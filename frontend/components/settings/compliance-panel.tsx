import { CheckCircle2, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const controls = [
  { label: "US-first baseline", state: "warning" as const, note: "Baseline policy shell only; legal review still required before live sending." },
  { label: "Suppression", state: "passed" as const, note: "Suppression UX is present with local/demo rows." },
  { label: "Unsubscribe", state: "pending" as const, note: "Persistence and email footer enforcement require backend routes." },
  { label: "Manual approval", state: "warning" as const, note: "Human review never bypasses safety or send gates." },
  { label: "Send gate", state: "blocked" as const, note: "Real sending is disabled in local/mock MVP." },
  { label: "Live sending review", state: "blocked" as const, note: "Production compliance review pending." },
];

export function CompliancePanel() {
  return (
    <BentoCard title="Compliance baseline" description="Compliance summary shell. Live sending review is required before production." badge="US-first shell">
      <div className="grid gap-3 md:grid-cols-2">
        {controls.map((control) => (
          <div key={control.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  {control.state === "blocked" ? <ShieldAlert className="size-4" /> : <CheckCircle2 className="size-4" />}
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
