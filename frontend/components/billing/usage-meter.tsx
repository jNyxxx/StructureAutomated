import { BentoCard } from "@/components/dashboard/bento-card";
import type { UsageSnapshot } from "@/lib/schemas";

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

export function UsageMeter({ usage, loading }: { usage: UsageSnapshot | null; loading: boolean }) {
  if (loading || !usage) {
    return (
      <BentoCard title="Usage meters" description="Local/mock usage only. Quota is not enforced in this demo." badge="Loading">
        <div className="flex h-32 items-center justify-center text-small text-muted">
          Loading actual usage metrics...
        </div>
      </BentoCard>
    );
  }

  return (
    <BentoCard title="Usage meters" description="Local/mock usage only. Real Stripe quotas are deferred." badge="Read-only">
      <div className="grid gap-3 md:grid-cols-2">
        <Meter label="Prospects" used={usage.contacts_total} limit={250} />
        <Meter label="Campaigns" used={usage.campaigns_total} limit={10} />
        <Meter label="Draft runs" used={usage.drafts_total} limit={100} />
        <Meter label="Outbound messages" used={usage.outbound_mock_sent} limit={500} />
      </div>
    </BentoCard>
  );
}
