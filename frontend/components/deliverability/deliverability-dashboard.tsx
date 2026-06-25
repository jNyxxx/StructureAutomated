"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Globe2 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { ErrorState } from "@/components/states";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchDeliverability, fetchDeliverabilityMailboxes } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { isStrictBackendMode } from "@/lib/runtime-mode";
import { useTenantContext } from "@/lib/tenant-context";
import { DeliverabilitySummaryCards } from "./deliverability-summary-cards";
import { DeliverabilityTrendChart } from "./deliverability-trend-chart";
import {
  deliverabilitySummary,
  deliverabilityToTrend,
  deliverabilityToView,
  domainAuthStatuses,
  mailboxDtoToHealth,
  mailboxHealth,
  type DeliverabilitySummaryView,
  type MailboxHealth,
} from "./deliverability-sample-data";
import { MailboxHealthCard } from "./mailbox-health-card";
import { SendGateHealthPanel } from "./send-gate-health-panel";
import { ThrottlePanel } from "./throttle-panel";
import { WarmupTimeline } from "./warmup-timeline";

export function DeliverabilityDashboard() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const strictBackendMode = isStrictBackendMode();
  const [summary, setSummary] = useState<DeliverabilitySummaryView>(deliverabilitySummary);
  const [mailboxes, setMailboxes] = useState<MailboxHealth[]>(mailboxHealth);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [strictError, setStrictError] = useState<string | null>(null);

  const loadDeliverability = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      if (strictBackendMode) {
        setStrictError("Deliverability backend mock API read did not complete in strict backend mode.");
        setLoading(false);
        return;
      }
      setSummary(deliverabilitySummary);
      setMailboxes(mailboxHealth);
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const [deliverabilityRes, mailboxRes] = await Promise.all([
        fetchDeliverability({ getToken: auth.getToken, getTenantId: () => selectedTenantId }),
        fetchDeliverabilityMailboxes({ getToken: auth.getToken, getTenantId: () => selectedTenantId }),
      ]);
      setSummary(deliverabilityToView(deliverabilityRes.deliverability));
      setMailboxes(mailboxDtoToHealth(mailboxRes.mailbox_health));
      setUsingFallback(false);
      setStrictError(null);
    } catch (err) {
      if (strictBackendMode) {
        setStrictError("NETWORK_ERROR: Deliverability backend mock API read failed in strict backend mode.");
      } else {
        console.error("Failed to load deliverability, falling back to read-only local/mock deliverability data:", err);
        setSummary(deliverabilitySummary);
        setMailboxes(mailboxHealth);
        setUsingFallback(true);
      }
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, strictBackendMode]);

  useEffect(() => {
    loadDeliverability();
  }, [loadDeliverability]);

  const trend = useMemo(() => deliverabilityToTrend(summary), [summary]);

  if (strictError) {
    return <ErrorState title="Strict backend mode: deliverability unavailable" description={strictError} />;
  }

  return (
    <>
      <Card className="border-yellow/25 bg-warnbg/60">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <CardTitle>Read-only backend mock deliverability notice</CardTitle>
              <CardDescription>
                {loading
                  ? "Loading read-only backend mock API deliverability data..."
                  : usingFallback
                    ? "Backend unavailable or auth missing. Showing read-only local/mock deliverability data fixture fallback."
                    : "Deliverability and mailbox/domain health loaded from backend mock API. DNS checks, mailbox provider calls, real sends, webhooks, exports, and recalculation actions remain disabled."}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No real DNS checks" />
          <GateReasonBadge state="blocked" label="No provider calls" />
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state={usingFallback ? "pending" : "passed"} label={usingFallback ? "Fixture fallback" : "Deliverability API read-only"} />
        </CardContent>
      </Card>

      <DeliverabilitySummaryCards summary={summary} />

      <div className="grid gap-4 xl:grid-cols-2">
        <MailboxHealthCard mailboxes={mailboxes} />
        <BentoCard title="Domain authentication" description="DKIM/SPF/DMARC cards are read-only. No real DNS lookup, DNS write, provider sync, or verification action is performed." badge="DNS shell">
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
        <DeliverabilityTrendChart trend={trend} />
        <SendGateHealthPanel />
      </div>
    </>
  );
}
