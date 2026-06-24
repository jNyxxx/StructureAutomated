import Link from "next/link";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { CampaignBuilderShell } from "@/components/campaigns/campaign-builder-shell";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function NewCampaignPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign builder"
        title="New campaign"
        description="Visual-only builder shell. Creation and all mutation actions remain pending backend API."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Create API pending</Badge>
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
              <CardTitle>Builder is locked</CardTitle>
              <CardDescription>
                No campaign is persisted. Research, RAG, draft generation, review, mock send, follow-up, and export remain unavailable until backend routes exist.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No backend create" />
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No provider calls" />
        </CardContent>
      </Card>

      <CampaignBuilderShell />
    </section>
  );
}
