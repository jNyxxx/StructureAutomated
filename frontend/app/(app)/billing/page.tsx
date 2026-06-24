import { AlertTriangle, Building2, CreditCard } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { AccessMatrix } from "@/components/billing/access-matrix";
import { BillingLockBanner } from "@/components/billing/billing-lock-banner";
import { BillingStatusBadge } from "@/components/billing/billing-status-badge";
import { currentBilling } from "@/components/billing/billing-sample-data";
import { UsageMeter } from "@/components/billing/usage-meter";
import { BentoCard } from "@/components/dashboard/bento-card";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function BillingPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Billing and access gates"
        title="Billing"
        description="MVP mock billing model only. Real Stripe checkout, webhooks, portal, and money movement are deferred."
        actions={<><Badge variant="default">Local/mock MVP</Badge><Badge variant="locked">Real Stripe deferred</Badge></>}
      />
      <LocalMockNotice />
      <BillingLockBanner />

      <Card className="border-yellow/25 bg-warnbg/60">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow"><AlertTriangle className="size-5" /></div>
            <div>
              <CardTitle>Pending backend/Stripe notice</CardTitle>
              <CardDescription>No real checkout, payment data, Stripe calls, webhooks, customer portal, or money movement is wired.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="Stripe deferred" />
          <GateReasonBadge state="blocked" label="No real payment data" />
          <GateReasonBadge state="pending" label="Billing API pending" />
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <BentoCard title="Plan / subscription shell" description="Tenant → subscription → plan relationship preview only." badge="Read-only">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-medium border border-border bg-panel2 p-3"><div className="flex items-center gap-2 text-small font-semibold text-text"><Building2 className="size-4 text-blue" /> Tenant</div><p className="mt-2 text-small text-muted">{currentBilling.tenant}</p></div>
            <div className="rounded-medium border border-border bg-panel2 p-3"><div className="flex items-center gap-2 text-small font-semibold text-text"><CreditCard className="size-4 text-blue" /> Plan</div><p className="mt-2 text-small text-muted">{currentBilling.plan}</p></div>
            <div className="rounded-medium border border-border bg-panel2 p-3"><p className="text-small font-semibold text-text">Subscription</p><p className="mt-2 text-caption text-muted">{currentBilling.subscription}</p></div>
            <div className="rounded-medium border border-border bg-panel2 p-3"><p className="text-small font-semibold text-text">tenant_status</p><div className="mt-2"><BillingStatusBadge state={currentBilling.state} /></div></div>
          </div>
        </BentoCard>
        <UsageMeter />
      </div>

      <AccessMatrix />
    </section>
  );
}
