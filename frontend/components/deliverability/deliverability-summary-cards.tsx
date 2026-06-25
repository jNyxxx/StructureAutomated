import { Ban, CopyX, Mail, ShieldAlert, SkipForward, Timer } from "lucide-react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { deliverabilitySummary, type DeliverabilitySummaryView } from "./deliverability-sample-data";

export function DeliverabilitySummaryCards({ summary = deliverabilitySummary }: { summary?: DeliverabilitySummaryView }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard title="Mock sends" value={String(summary.mockSends)} description="Backend mock API/local data only; no provider call." icon={Mail} status="Read-only" />
      <MetricCard title="Blocked" value={String(summary.blocked)} description="Safety/access/send gate blocks." icon={Ban} status="No-send" tone="locked" />
      <MetricCard title="Duplicates" value={String(summary.duplicates)} description="Duplicate contacts skipped." icon={CopyX} status="Skipped" tone="warning" />
      <MetricCard title="Suppressed" value={String(summary.suppressed)} description="Suppression/compliance blocks." icon={ShieldAlert} status="Blocked" tone="locked" />
      <MetricCard title="Safety denied" value={String(summary.safetyDenied)} description="Prompt/grounding/send safety denied." icon={ShieldAlert} status="Denied" tone="locked" />
      <MetricCard title="Throttled" value={String(summary.throttled)} description="Read-only throttle denials." icon={Timer} status="Preview" tone="warning" />
      <MetricCard title="Follow-ups sent" value={String(summary.followUpsSent)} description="Mock/local follow-up count only." icon={Mail} status="No real sends" tone="locked" />
      <MetricCard title="Follow-ups skipped" value={String(summary.followUpsSkipped)} description="Suppression/throttle/safety skipped." icon={SkipForward} status="Skipped" tone="warning" />
    </div>
  );
}
