"use client";

import { AlertTriangle, Building2, ShieldCheck } from "lucide-react";

import { BillingStatusBadge, GateReasonBadge } from "@/components/badges";
import { ActivityPreview } from "@/components/dashboard/activity-preview";
import { BentoCard } from "@/components/dashboard/bento-card";
import { DeliverabilityOutcomesPreview } from "@/components/dashboard/deliverability-outcomes-preview";
import { FlowProgress } from "@/components/dashboard/flow-progress";
import { GateHealthPanel } from "@/components/dashboard/gate-health-panel";
import { MetricCard } from "@/components/dashboard/metric-card";
import { PipelinePreview } from "@/components/dashboard/pipeline-preview";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { ReadinessPanel } from "@/components/dashboard/readiness-panel";
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
        description="Local/mock MVP command center using only mounted auth and health routes. Product metrics below are demo-safe placeholders until product APIs are mounted."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            {tenant.role ? <Badge variant="success">{tenant.role}</Badge> : <Badge variant="warning">Role pending</Badge>}
          </>
        }
      />

      <div className="rounded-xl border border-yellow/30 bg-warnbg p-4 text-small text-muted shadow-panel">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <p className="font-semibold text-text">Production is not approved</p>
              <p className="mt-1">
                Phase 1 backend local/mock evidence is complete through P1-13. Live DB smoke, production deployment, real sending, billing, and provider integrations remain deferred.
              </p>
            </div>
          </div>
          <GateReasonBadge state="blocked" label="No production" />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Tenant"
          value={tenant.isConfirmed ? "Confirmed" : "Pending"}
          description={tenant.confirmedTenantId ?? "Waiting for /auth/me confirmation."}
          icon={Building2}
          tone={tenant.isConfirmed ? "success" : "warning"}
          status={tenant.status}
        />
        <MetricCard
          title="Billing gate"
          value="Read-only"
          description="Mock billing state shown; real Stripe is not implemented."
          icon={ShieldCheck}
          tone="locked"
          status="Mock only"
        />
        <MetricCard
          title="Mounted APIs"
          value="7"
          description="Only auth and health/ready/live routes are wired."
          icon={ShieldCheck}
          tone="success"
          status="Allowed"
        />
        <BentoCard title="Access summary" description="Frontend hides/locks only; backend remains authority." badge="Gated">
          <div className="flex flex-wrap gap-2">
            <BillingStatusBadge state="inactive" />
            <GateReasonBadge state="blocked" label="Send locked" />
            <GateReasonBadge state="pending" label="Product APIs pending" />
          </div>
        </BentoCard>
      </div>

      <ReadinessPanel />

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

      <BentoCard title="Evidence note" description="Implementation evidence is local/mock only and must not be presented as production approval." badge="P1-13 complete">
        <p className="text-small text-muted">
          Phase 1 backend local/mock MVP is complete through P1-13. Frontend dashboard FE-6 uses demo-safe placeholder data for product sections and only calls mounted auth/health readiness routes through existing FE-4 wiring.
        </p>
      </BentoCard>
    </section>
  );
}
