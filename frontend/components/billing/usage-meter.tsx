import { BentoCard } from "@/components/dashboard/bento-card";
import { currentBilling } from "./billing-sample-data";

function Meter({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = Math.min(100, Math.round((used / limit) * 100));
  return (
    <div className="rounded-medium border border-border bg-panel2 p-3">
      <div className="flex items-center justify-between gap-3 text-small">
        <span className="font-semibold text-text">{label}</span>
        <span className="text-muted">{used}/{limit}</span>
      </div>
      <div className="mt-3 h-2 rounded-pill bg-panel">
        <div className="h-2 rounded-pill bg-blue" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function UsageMeter() {
  const usage = currentBilling.usage;
  return (
    <BentoCard title="Usage meters" description="Local/mock usage only. Backend billing/quota enforcement is not wired from this UI." badge="Read-only">
      <div className="grid gap-3 md:grid-cols-2">
        <Meter label="Prospects" {...usage.prospects} />
        <Meter label="Campaigns" {...usage.campaigns} />
        <Meter label="Draft runs" {...usage.draftRuns} />
        <Meter label="Exports" {...usage.exports} />
      </div>
    </BentoCard>
  );
}
