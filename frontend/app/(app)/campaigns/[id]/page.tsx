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
        description="Monitor campaign progress, metrics, and draft approvals."
        actions={<Button asChild variant="secondary">
              <Link href="/campaigns">
                <ArrowLeft className="size-4" /> Back to campaigns
              </Link>
            </Button>}
      />

      <CampaignDetail campaign={campaign} />
    </section>
  );
}
