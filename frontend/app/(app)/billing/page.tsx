"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Building2, CreditCard } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { AccessMatrix } from "@/components/billing/access-matrix";
import { BillingLockBanner } from "@/components/billing/billing-lock-banner";
import { BillingStatusBadge } from "@/components/billing/billing-status-badge";
import { UsageMeter } from "@/components/billing/usage-meter";
import { BentoCard } from "@/components/dashboard/bento-card";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { fetchUsage } from "@/lib/backend-api";
import type { UsageSnapshot } from "@/lib/schemas";

export default function BillingPage() {
  const auth = useFrontendAuth();
  const { selectedTenantId, billingSubscription, billingAccess } = useTenantContext();
  const [usage, setUsage] = useState<UsageSnapshot | null>(null);
  const [loadingUsage, setLoadingUsage] = useState(true);

  const loadUsage = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) return;
    setLoadingUsage(true);
    try {
      const res = await fetchUsage({
        getToken: auth.getToken,
        getTenantId: () => selectedTenantId,
      });
      setUsage(res.usage);
    } catch (err) {
      console.error("Failed to fetch usage:", err);
    } finally {
      setLoadingUsage(false);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadUsage();
  }, [loadUsage]);

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Billing and access gates"
        title="Billing"
        description="MVP mock billing model only. Real Stripe checkout, webhooks, portal, and money movement are deferred."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Real Stripe deferred</Badge>
          </>
        }
      />
      <LocalMockNotice />
      <BillingLockBanner />

      <Card className="border-yellow/25 bg-warnbg/60">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <CardTitle>Pending backend/Stripe notice</CardTitle>
              <CardDescription>
                No real checkout, payment data, Stripe calls, webhooks, customer portal, or money movement is wired.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="Stripe deferred" />
          <GateReasonBadge state="blocked" label="No real payment data" />
          {!billingSubscription && <GateReasonBadge state="pending" label="Billing API loading" />}
          {billingSubscription && <GateReasonBadge state="passed" label="Billing API wired" />}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <BentoCard title="Plan / subscription shell" description="Mock MVP subscription and plan info mapped from backend." badge="Read-only">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-small font-semibold text-text">
                <Building2 className="size-4 text-blue" /> Tenant ID
              </div>
              <p className="mt-2 text-caption text-muted truncate">{selectedTenantId ?? "None"}</p>
            </div>
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-small font-semibold text-text">
                <CreditCard className="size-4 text-blue" /> Active Plan
              </div>
              <p className="mt-2 text-small text-muted font-semibold">{billingSubscription?.plan?.name ?? "None"}</p>
            </div>
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <p className="text-small font-semibold text-text">Grace Expiry</p>
              <p className="mt-2 text-caption text-muted truncate">
                {billingSubscription?.grace_until
                  ? new Date(billingSubscription.grace_until).toLocaleString()
                  : "None"}
              </p>
            </div>
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <p className="text-small font-semibold text-text">tenant_status</p>
              <div className="mt-2">
                <BillingStatusBadge state={(billingSubscription?.tenant_status as any) ?? "inactive"} />
              </div>
            </div>
          </div>
        </BentoCard>
        <UsageMeter usage={usage} loading={loadingUsage} />
      </div>

      <AccessMatrix billingAccess={billingAccess} />
    </section>
  );
}
