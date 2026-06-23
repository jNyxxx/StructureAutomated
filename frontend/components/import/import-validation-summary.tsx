import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";

const items = [
  { label: "Valid preview rows", value: "1", icon: CheckCircle2, tone: "text-green" },
  { label: "Needs review", value: "1", icon: AlertTriangle, tone: "text-yellow" },
  { label: "Suppression blocked", value: "1", icon: ShieldAlert, tone: "text-red" },
];

export function ImportValidationSummary() {
  return (
    <div className="rounded-xl border border-border bg-panel p-5 shadow-panel">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-h3 text-text">Validation summary</h2>
          <p className="mt-1 text-small text-muted">Local validation preview only. Backend import validation route is not mounted.</p>
        </div>
        <GateReasonBadge state="blocked" label="Import disabled" />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-small font-semibold text-text">
                <Icon className={`size-4 ${item.tone}`} /> {item.label}
              </div>
              <p className="mt-2 text-h2 text-text">{item.value}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
