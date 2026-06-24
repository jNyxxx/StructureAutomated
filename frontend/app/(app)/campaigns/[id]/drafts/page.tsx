import Link from "next/link";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { getCampaignById } from "@/components/campaigns/campaign-sample-data";
import { DraftsTable } from "@/components/drafts/drafts-table";
import { getDraftsByCampaignId } from "@/components/drafts/draft-sample-data";
import { ResearchWorkbench } from "@/components/research/research-workbench";
import { PageHeader } from "@/components/layout/page-header";
import { ErrorState, LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function CampaignDraftsPage({ params }: { params: { id: string } }) {
  const campaign = getCampaignById(params.id);
  const rows = getDraftsByCampaignId(params.id);

  if (!campaign) {
    return <ErrorState title="Campaign demo row not found" description="Only local/demo campaign IDs are available in this frontend slice." />;
  }

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign drafts"
        title={`${campaign.name} drafts`}
        description="Campaign-scoped draft and Research/RAG shell. No backend draft, research, approval, or send APIs are called."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Button asChild variant="secondary">
              <Link href={`/campaigns/${campaign.id}`}>
                <ArrowLeft className="size-4" /> Back to campaign
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
              <CardTitle>Campaign draft actions are locked</CardTitle>
              <CardDescription>
                Generate, regenerate, approve, send, export, scrape, enrich, and embedding-provider actions remain disabled until backend routes exist.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="pending" label="Draft API pending" />
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="blocked" label="No provider calls" />
          <GateReasonBadge state="blocked" label="No live scraping" />
        </CardContent>
      </Card>

      <DraftsTable rows={rows} />
      <ResearchWorkbench />
    </section>
  );
}
