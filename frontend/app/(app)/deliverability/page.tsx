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
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function DeliverabilityPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Send safety dashboard"
        title="Deliverability"
        description="Demo-safe deliverability workspace using local data only. No DNS checks, mailbox provider calls, or real sending are performed."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
          </>
        }
      />

      <LocalMockNotice />

      <Card className="border-yellow/25 bg-warnbg/60">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <CardTitle>Pending backend/provider notice</CardTitle>
              <CardDescription>
                Deliverability data is local/demo only. DNS checks, mailbox health providers, real sends, SMS, webhooks, Stripe, and live scraping are not connected.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No real DNS checks" />
          <GateReasonBadge state="blocked" label="No provider calls" />
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="pending" label="Deliverability API pending" />
        </CardContent>
      </Card>

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
