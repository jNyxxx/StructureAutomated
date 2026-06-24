import Link from "next/link";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { CampaignDetail } from "@/components/campaigns/campaign-detail";
import { getCampaignById } from "@/components/campaigns/campaign-sample-data";
import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { ErrorState, LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  const campaign = getCampaignById(params.id);

  if (!campaign) {
    return <ErrorState title="Campaign demo row not found" description="Only local/demo campaign IDs are available in this frontend slice." />;
  }

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign detail"
        title={campaign.name}
        description="Read-only local/demo campaign detail. No mutation, provider, sending, schedule, export, or campaign APIs are called."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
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
              <CardTitle>Actions locked until backend APIs exist</CardTitle>
              <CardDescription>
                Create campaign, add/remove contacts, start research, generate drafts, approve drafts, mock send, schedule follow-up, and export are disabled.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No provider calls" />
          <GateReasonBadge state="pending" label="Campaign API pending" />
        </CardContent>
      </Card>

      <CampaignDetail campaign={campaign} />
    </section>
  );
}
