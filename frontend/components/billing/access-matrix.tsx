import { Lock, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { mockBillingStates } from "./billing-sample-data";
import { BillingStatusBadge } from "./billing-status-badge";
import type { BillingAccess } from "@/lib/schemas";

export function AccessMatrix({ billingAccess }: { billingAccess: BillingAccess | null }) {
  const gates = [
    {
      key: "can_send",
      label: "Can send",
      allowed: billingAccess ? billingAccess.can_send : false,
      reason: billingAccess && billingAccess.can_send
        ? "Tenant is active; sending is enabled."
        : "Subscription is inactive or locked; sending is blocked.",
    },
    {
      key: "can_run_agents",
      label: "Can run agents",
      allowed: billingAccess ? billingAccess.can_run_agents : false,
      reason: billingAccess && billingAccess.can_run_agents
        ? "Tenant is active; AI agents research/runs are enabled."
        : "Subscription is inactive or locked; agent runs are blocked.",
    },
    {
      key: "can_create_campaign",
      label: "Can create campaign",
      allowed: billingAccess ? billingAccess.can_create_campaign : false,
      reason: billingAccess && billingAccess.can_create_campaign
        ? "Tenant is active; new campaigns can be created."
        : "Subscription is inactive or locked; campaign creation is blocked.",
    },
    {
      key: "can_export",
      label: "Can export",
      allowed: billingAccess ? billingAccess.can_export : false,
      reason: billingAccess && billingAccess.can_export
        ? "Tenant is active; data downloads and exports are allowed."
        : "Subscription is inactive or locked; export is blocked.",
    },
  ];

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
          {gates.map((gate) => (
            <div key={gate.key} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex gap-3">
                  <div className={`flex size-9 items-center justify-center rounded-small ${gate.allowed ? "bg-goodbg text-green" : "bg-redbg text-red"}`}>
                    {gate.allowed ? <ShieldCheck className="size-4" /> : <Lock className="size-4" />}
                  </div>
                  <div>
                    <p className="text-small font-semibold text-text">{gate.label} ({gate.key})</p>
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
