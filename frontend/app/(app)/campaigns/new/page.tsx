import Link from "next/link";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { CampaignBuilderShell } from "@/components/campaigns/campaign-builder-shell";
import { PageHeader } from "@/components/layout/page-header";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function NewCampaignPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign builder"
        title="New campaign"
        description="Create a new outreach campaign targeting prospective leads."
        actions={<Button asChild variant="secondary">
              <Link href="/campaigns">
                <ArrowLeft className="size-4" /> Back to campaigns
              </Link>
            </Button>}
      />

      <CampaignBuilderShell />
    </section>
  );
}
