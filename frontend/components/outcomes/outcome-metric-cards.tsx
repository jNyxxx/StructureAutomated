import { BarChart3, CalendarCheck, DollarSign, Mail, MessageSquare, Target } from "lucide-react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { outcomeMetrics, type OutcomeMetricsView } from "./outcomes-sample-data";

export function OutcomeMetricCards({ metrics = outcomeMetrics }: { metrics?: OutcomeMetricsView }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <MetricCard title="Mock sends" value={String(metrics.mockSent)} description="Backend mock API/local sends only." icon={Mail} status="Read-only" />
      <MetricCard title="Replies" value={String(metrics.replies)} description="Read-only local/mock outcome events." icon={MessageSquare} status="Preview" tone="warning" />
      <MetricCard title="Meetings" value={String(metrics.meetings)} description="Mock-only attribution." icon={CalendarCheck} status="Assumption" tone="warning" />
      <MetricCard title="Opportunities" value={String(metrics.opportunities)} description="No CRM integration." icon={Target} status="No CRM" tone="locked" />
      <MetricCard title="Pipeline value" value={metrics.pipelineValue} description="Mock pipeline estimate only, not real revenue." icon={DollarSign} status="Not revenue" tone="warning" />
      <MetricCard title="Mock cost" value={metrics.estimatedCost} description="No Stripe/payment data." icon={BarChart3} status={metrics.estimatedRoi} tone="locked" />
    </div>
  );
}
