import { Lock, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { derivedGates, mockBillingStates } from "./billing-sample-data";
import { BillingStatusBadge } from "./billing-status-badge";

export function AccessMatrix() {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <BentoCard title="Mock billing states" description="MVP billing state model only. Real Stripe comes later." badge="State machine">
        <div className="space-y-3">
          {mockBillingStates.map((row) => (
            <div key={row.state} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2">
                  <BillingStatusBadge state={row.state} />
                  <span className="text-caption text-muted">tenant_status: {row.tenantStatus}</span>
                </div>
                <GateReasonBadge state={row.access === "allowed" ? "passed" : row.access === "limited" ? "warning" : "blocked"} label={row.access} />
              </div>
              <p className="mt-2 text-caption text-muted">{row.note}</p>
            </div>
          ))}
        </div>
      </BentoCard>

      <BentoCard title="Derived access gates" description="Frontend display only; backend central gates remain source of truth." badge="Gate cards">
        <div className="space-y-3">
          {derivedGates.map((gate) => (
            <div key={gate.key} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex gap-3">
                  <div className="flex size-9 items-center justify-center rounded-small bg-redbg text-red">
                    {gate.allowed ? <ShieldCheck className="size-4" /> : <Lock className="size-4" />}
                  </div>
                  <div>
                    <p className="text-small font-semibold text-text">{gate.key}</p>
                    <p className="text-caption text-muted">{gate.reason}</p>
                  </div>
                </div>
                <GateReasonBadge state={gate.allowed ? "passed" : "blocked"} label={gate.allowed ? "allowed" : "locked"} />
              </div>
            </div>
          ))}
        </div>
      </BentoCard>
    </div>
  );
}
