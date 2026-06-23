import { ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { sendGateHealth } from "./deliverability-sample-data";

export function SendGateHealthPanel() {
  return (
    <BentoCard title="Send gate health" description="Backend remains source of truth; this is a read-only visual gate preview." badge="No-send">
      <div className="space-y-3">
        {sendGateHealth.map((gate) => (
          <div key={gate.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <ShieldCheck className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{gate.label}</p>
                  <p className="text-caption text-muted">{gate.note}</p>
                </div>
              </div>
              <GateReasonBadge state={gate.state} />
            </div>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
