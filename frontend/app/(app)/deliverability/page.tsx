import { AlertTriangle, Globe2 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DeliverabilitySummaryCards } from "@/components/deliverability/deliverability-summary-cards";
import { DeliverabilityTrendChart } from "@/components/deliverability/deliverability-trend-chart";
import { domainAuthStatuses } from "@/components/deliverability/deliverability-sample-data";
import { MailboxHealthCard } from "@/components/deliverability/mailbox-health-card";
import { SendGateHealthPanel } from "@/components/deliverability/send-gate-health-panel";
import { ThrottlePanel } from "@/components/deliverability/throttle-panel";
import { WarmupTimeline } from "@/components/deliverability/warmup-timeline";
import { BentoCard } from "@/components/dashboard/bento-card";
import { PageHeader } from "@/components/layout/page-header";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function DeliverabilityPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Send safety dashboard"
        title="Deliverability"
        description="Monitor mailbox pool health, warming progress, and domain authentication status."

      />

      <DeliverabilitySummaryCards />

      <div className="grid gap-4 xl:grid-cols-2">
        <MailboxHealthCard />
        <BentoCard title="Domain authentication" description="DKIM/SPF/DMARC cards are demo/read-only. No DNS lookup is performed." badge="DNS shell">
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
            {domainAuthStatuses.map((item) => (
              <div key={item.label} className="rounded-medium border border-border bg-panel2 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 text-small font-semibold text-text">
                    <Globe2 className="size-4 text-blue" /> {item.label}
                  </div>
                  <GateReasonBadge state={item.state} label={item.status} />
                </div>
              </div>
            ))}
          </div>
        </BentoCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <WarmupTimeline />
        <ThrottlePanel />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <DeliverabilityTrendChart />
        <SendGateHealthPanel />
      </div>
    </section>
  );
}
