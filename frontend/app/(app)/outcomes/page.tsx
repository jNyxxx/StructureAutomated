import { AlertTriangle, ScrollText } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CampaignOutcomesTable } from "@/components/outcomes/campaign-outcomes-table";
import { FunnelSummary } from "@/components/outcomes/funnel-summary";
import { OutcomeMetricCards } from "@/components/outcomes/outcome-metric-cards";
import { RoiSummaryCard } from "@/components/outcomes/roi-summary-card";
import { RoiTrendChart } from "@/components/outcomes/roi-trend-chart";

export default function OutcomesPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Outcome intelligence"
        title="Outcomes and ROI"
        description="Demo-safe outcomes dashboard using local assumptions only. No CRM, payment, revenue, attribution, or Stripe data is connected."
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
              <CardTitle>Read-only local assumptions</CardTitle>
              <CardDescription>
                ROI and outcomes are preview data only. This page does not imply live CRM, payment, revenue, attribution, Stripe, SMS, webhooks, or provider integrations.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No real Stripe/payment data" />
          <GateReasonBadge state="blocked" label="No CRM sync" />
          <GateReasonBadge state="blocked" label="No live attribution" />
          <GateReasonBadge state="pending" label="Outcomes API pending" />
        </CardContent>
      </Card>

      <OutcomeMetricCards />

      <div className="grid gap-4 xl:grid-cols-2">
        <FunnelSummary />
        <RoiSummaryCard />
      </div>

      <RoiTrendChart />

      <BentoCard title="Idempotency and outcome events" description="Read-only shell showing how future outcome ingestion should stay safe and deduplicated." badge="Event shell">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ScrollText className="size-4 text-blue" /> Idempotency key
            </div>
            <p className="mt-2 text-caption text-muted">Future outcome events must be deduped by stable event key.</p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ScrollText className="size-4 text-yellow" /> Source trust
            </div>
            <p className="mt-2 text-caption text-muted">CRM/payment attribution sources remain disconnected in this slice.</p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ScrollText className="size-4 text-red" /> Mutation lock
            </div>
            <p className="mt-2 text-caption text-muted">Export/sync/recalculate actions are pending backend API.</p>
          </div>
        </div>
      </BentoCard>

      <CampaignOutcomesTable />
    </section>
  );
}
