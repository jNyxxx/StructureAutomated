"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { CampaignDetail } from "@/components/campaigns/campaign-detail";
import { campaignToRow, getCampaignById, type CampaignRow } from "@/components/campaigns/campaign-sample-data";
import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { ErrorState, LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchCampaign } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const fallbackCampaign = getCampaignById(params.id);
  const [campaign, setCampaign] = useState<CampaignRow | undefined>(fallbackCampaign);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(Boolean(fallbackCampaign));

  const loadCampaign = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setCampaign(fallbackCampaign);
      setUsingFallback(Boolean(fallbackCampaign));
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await fetchCampaign(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        params.id,
      );
      setCampaign(campaignToRow(res.campaign));
      setUsingFallback(false);
    } catch (err) {
      console.error("Failed to load campaign detail, falling back to read-only local/mock data:", err);
      setCampaign(fallbackCampaign);
      setUsingFallback(Boolean(fallbackCampaign));
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, params.id, fallbackCampaign]);

  useEffect(() => {
    loadCampaign();
  }, [loadCampaign]);

  if (!campaign) {
    return <ErrorState title="Campaign read-only row not found" description="Only backend mock API campaigns or local/mock fixture campaign IDs are available in this frontend slice." />;
  }

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign detail"
        title={campaign.name}
        description="Read-only campaign detail from the backend mock API or fixture fallback. No mutation, provider, sending, schedule, export, research, draft, or campaign action is enabled."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Badge variant={usingFallback ? "locked" : "default"}>{loading ? "Loading" : usingFallback ? "Fixture fallback" : "Backend mock API"}</Badge>
            <Button asChild variant="secondary">
              <Link href="/campaigns">
                <ArrowLeft className="size-4" /> Back to campaigns
              </Link>
            </Button>
          </>
        }
      />

      <LocalMockNotice />

      <Card className="border-yellow/25 bg-warnbg/60">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <CardTitle>Actions locked for read-only campaign wiring</CardTitle>
              <CardDescription>
                Create campaign, update campaign, add/remove contacts, start research, generate drafts, approve drafts, mock send, schedule follow-up, and export are disabled.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No provider calls" />
          <GateReasonBadge state="passed" label="Campaign API read-only" />
        </CardContent>
      </Card>

      <CampaignDetail campaign={campaign} />
    </section>
  );
}
