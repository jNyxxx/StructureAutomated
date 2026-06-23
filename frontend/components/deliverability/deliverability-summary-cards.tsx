import { Ban, CopyX, Mail, ShieldAlert, SkipForward, Timer } from "lucide-react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { deliverabilitySummary } from "./deliverability-sample-data";

export function DeliverabilitySummaryCards() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard title="Mock sends" value={String(deliverabilitySummary.mockSends)} description="Local/mock sends only; no provider call." icon={Mail} status="Demo" />
      <MetricCard title="Blocked" value={String(deliverabilitySummary.blocked)} description="Safety/access/send gate blocks." icon={Ban} status="No-send" tone="locked" />
      <MetricCard title="Duplicates" value={String(deliverabilitySummary.duplicates)} description="Duplicate contacts skipped." icon={CopyX} status="Skipped" tone="warning" />
      <MetricCard title="Suppressed" value={String(deliverabilitySummary.suppressed)} description="Suppression/compliance blocks." icon={ShieldAlert} status="Blocked" tone="locked" />
      <MetricCard title="Safety denied" value={String(deliverabilitySummary.safetyDenied)} description="Prompt/grounding/send safety denied." icon={ShieldAlert} status="Denied" tone="locked" />
      <MetricCard title="Follow-ups scheduled" value={String(deliverabilitySummary.followUpsScheduled)} description="Schedule preview only." icon={Timer} status="Preview" tone="warning" />
      <MetricCard title="Follow-ups sent" value={String(deliverabilitySummary.followUpsSent)} description="Real sending disabled." icon={Mail} status="0 real sends" tone="locked" />
      <MetricCard title="Follow-ups skipped" value={String(deliverabilitySummary.followUpsSkipped)} description="Suppression/throttle/safety skipped." icon={SkipForward} status="Skipped" tone="warning" />
    </div>
  );
}
