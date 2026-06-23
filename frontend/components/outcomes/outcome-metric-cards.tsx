import { BarChart3, CalendarCheck, DollarSign, Mail, MessageSquare, Target } from "lucide-react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { outcomeMetrics } from "./outcomes-sample-data";

export function OutcomeMetricCards() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <MetricCard title="Mock sends" value={String(outcomeMetrics.mockSent)} description="Local/demo sends only." icon={Mail} status="Demo" />
      <MetricCard title="Replies" value={String(outcomeMetrics.replies)} description="Sample outcome events." icon={MessageSquare} status="Preview" tone="warning" />
      <MetricCard title="Meetings" value={String(outcomeMetrics.meetings)} description="Demo-only attribution." icon={CalendarCheck} status="Assumption" tone="warning" />
      <MetricCard title="Opportunities" value={String(outcomeMetrics.opportunities)} description="No CRM integration." icon={Target} status="No CRM" tone="locked" />
      <MetricCard title="Pipeline value" value={outcomeMetrics.pipelineValue} description="Demo assumption only." icon={DollarSign} status="Not revenue" tone="warning" />
      <MetricCard title="Demo cost" value={outcomeMetrics.estimatedCost} description="No Stripe/payment data." icon={BarChart3} status="Assumption" tone="locked" />
    </div>
  );
}
