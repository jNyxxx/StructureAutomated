"use client";

import { Building2, ShieldCheck } from "lucide-react";

import { BillingStatusBadge, GateReasonBadge } from "@/components/badges";
import { ActivityPreview } from "@/components/dashboard/activity-preview";
import { BentoCard } from "@/components/dashboard/bento-card";
import { DeliverabilityOutcomesPreview } from "@/components/dashboard/deliverability-outcomes-preview";
import { FlowProgress } from "@/components/dashboard/flow-progress";
import { GateHealthPanel } from "@/components/dashboard/gate-health-panel";
import { MetricCard } from "@/components/dashboard/metric-card";
import { PipelinePreview } from "@/components/dashboard/pipeline-preview";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { useTenantContext } from "@/lib/tenant-context";

export default function DashboardPage() {
  const tenant = useTenantContext();

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Command center"
        title="Dashboard"
        description="Overview of your outreach campaigns, prospect pipeline, and deliverability status."
        actions={
          <>

            {tenant.role ? <Badge variant="success">{tenant.role}</Badge> : <Badge variant="warning">Role pending</Badge>}
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Tenant"
          value="Confirmed"
          description="Workspace: default-tenant"
          icon={Building2}
          tone={tenant.isConfirmed ? "success" : "warning"}
          status={tenant.status}
        />
        <MetricCard
          title="Billing gate"
          value="Read-only"
          description="Enterprise billing active."
          icon={ShieldCheck}
          tone="success"
          status="Good"
        />
        <MetricCard
          title="Mounted APIs"
          value="Active"
          description="All workspace APIs healthy."
          icon={ShieldCheck}
          tone="success"
          status="Operational"
        />
        <BentoCard title="Access summary" description="All RAG-grounded safety policies and send gates are monitored dynamically." badge="Active">
          <div className="flex flex-wrap gap-2">
            <BillingStatusBadge state="active" />
            <GateReasonBadge state="passed" label="Send gate active" />
            <GateReasonBadge state="passed" label="All APIs operational" />
          </div>
        </BentoCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <FlowProgress />
        <GateHealthPanel />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <PipelinePreview />
        <ActivityPreview />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <DeliverabilityOutcomesPreview />
        <QuickActions />
      </div>

    </section>
  );
}
