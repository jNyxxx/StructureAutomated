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
        description="AI-generated outreach drafts for this campaign."
        actions={<Button asChild variant="secondary">
              <Link href={`/campaigns/${campaign.id}`}>
                <ArrowLeft className="size-4" /> Back to campaign
              </Link>
            </Button>}
      />

      <DraftsTable rows={rows} />
      <ResearchWorkbench />
    </section>
  );
}
