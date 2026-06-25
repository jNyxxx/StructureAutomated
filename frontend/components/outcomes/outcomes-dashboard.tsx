"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Lock, ScrollText } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchOutcomes, fetchOutcomesRoi } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { isStrictBackendMode } from "@/lib/runtime-mode";
import type { RoiSummary } from "@/lib/schemas";
import { useTenantContext } from "@/lib/tenant-context";
import { CampaignOutcomesTable } from "./campaign-outcomes-table";
import { FunnelSummary } from "./funnel-summary";
import { OutcomeMetricCards } from "./outcome-metric-cards";
import {
  DEFAULT_ROI_CAMPAIGN_ID,
  campaignOutcomeRows,
  funnelSummary,
  outcomeMetrics,
  outcomesToFunnel,
  outcomesToMetrics,
  outcomesToRows,
  roiToTrend,
  type CampaignOutcomeRow,
  type OutcomeMetricsView,
} from "./outcomes-sample-data";
import { RoiSummaryCard } from "./roi-summary-card";
import { RoiTrendChart } from "./roi-trend-chart";

export function OutcomesDashboard() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const strictBackendMode = isStrictBackendMode();
  const [metrics, setMetrics] = useState<OutcomeMetricsView>(outcomeMetrics);
  const [funnel, setFunnel] = useState(funnelSummary);
  const [rows, setRows] = useState<CampaignOutcomeRow[]>(campaignOutcomeRows);
  const [roi, setRoi] = useState<RoiSummary | null>(null);
  const [runtime, setRuntime] = useState("read-only local/mock data");
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [strictError, setStrictError] = useState<string | null>(null);

  const loadOutcomes = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      if (strictBackendMode) {
        setStrictError("Outcomes require backend mock API reads in strict backend mode.");
        setLoading(false);
        return;
      }
      setMetrics(outcomeMetrics);
      setFunnel(funnelSummary);
      setRows(campaignOutcomeRows);
      setRoi(null);
      setRuntime("fixture fallback");
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const [outcomesRes, roiRes] = await Promise.all([
        fetchOutcomes({ getToken: auth.getToken, getTenantId: () => selectedTenantId }),
        fetchOutcomesRoi({ getToken: auth.getToken, getTenantId: () => selectedTenantId }, DEFAULT_ROI_CAMPAIGN_ID),
      ]);
      setMetrics(outcomesToMetrics(outcomesRes.outcomes, roiRes.roi));
      setFunnel(outcomesToFunnel(outcomesRes.outcomes, roiRes.roi.sent_count));
      setRows(outcomesToRows(outcomesRes.outcomes, roiRes.roi));
      setRoi(roiRes.roi);
      setRuntime("backend mock API");
      setUsingFallback(false);
      setStrictError(null);
    } catch (err) {
      if (strictBackendMode) {
        setStrictError("NETWORK_ERROR: Outcomes backend mock API read failed in strict backend mode.");
      } else {
        console.error("Failed to load outcomes/ROI, falling back to read-only local/mock outcomes data:", err);
        setMetrics(outcomeMetrics);
        setFunnel(funnelSummary);
        setRows(campaignOutcomeRows);
        setRoi(null);
        setRuntime("fixture fallback");
        setUsingFallback(true);
      }
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, strictBackendMode]);

  useEffect(() => {
    loadOutcomes();
  }, [loadOutcomes]);

  const trend = useMemo(() => roiToTrend(roi, metrics.replies), [metrics.replies, roi]);

  if (strictError) {
    return <ErrorState title="Strict backend mode: outcomes unavailable" description={strictError} />;
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
              <CardTitle>Read-only backend mock outcomes notice</CardTitle>
              <CardDescription>
                {loading
                  ? "Loading read-only backend mock API outcomes and ROI data..."
                  : usingFallback
                    ? "Backend unavailable or auth missing. Showing read-only local/mock outcomes data fixture fallback."
                    : "Outcomes and ROI loaded from backend mock API. Export, sync, recalculation, mock-event POST, CRM, ads, Stripe, payment, provider, and real attribution actions remain disabled."}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No real Stripe/payment data" />
          <GateReasonBadge state="blocked" label="No CRM sync" />
          <GateReasonBadge state="blocked" label="No live attribution" />
          <GateReasonBadge state={usingFallback ? "pending" : "passed"} label={usingFallback ? "Fixture fallback" : "Outcomes API read-only"} />
          <Button disabled variant="locked" size="sm">
            <Lock className="size-4" /> Export outcomes
          </Button>
          <Button disabled variant="locked" size="sm">
            <Lock className="size-4" /> Sync CRM
          </Button>
          <Button disabled variant="locked" size="sm">
            <Lock className="size-4" /> Recalculate ROI
          </Button>
          <Button disabled variant="locked" size="sm">
            <Lock className="size-4" /> Provider sync
          </Button>
        </CardContent>
      </Card>

      <OutcomeMetricCards metrics={metrics} />

      <div className="grid gap-4 xl:grid-cols-2">
        <FunnelSummary steps={funnel} />
        <RoiSummaryCard metrics={metrics} />
      </div>

      <RoiTrendChart trend={trend} />

      <BentoCard title="Idempotency and outcome events" description="Read-only shell showing how future outcome ingestion should stay safe and deduplicated. No mock-event POST, export, sync, recalculation, CRM, ads, Stripe, or provider action is wired." badge="Event shell">
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
            <p className="mt-2 text-caption text-muted">CRM/payment/ad attribution sources remain disconnected in this slice.</p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ScrollText className="size-4 text-red" /> Mutation lock
            </div>
            <p className="mt-2 text-caption text-muted">Export/sync/recalculate/mock-event actions are not wired.</p>
          </div>
        </div>
      </BentoCard>

      <CampaignOutcomesTable rows={rows} runtime={runtime} />
    </>
  );
}
