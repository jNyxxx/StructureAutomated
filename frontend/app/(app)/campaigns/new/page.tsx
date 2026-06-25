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
        description="Local/mock campaign builder using the backend mock API. Research, enrichment, scraping, drafts, sends, follow-ups, providers, and production remain disabled."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="default">Backend mock create</Badge>
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
              <CardTitle>Safe local/mock campaign create only</CardTitle>
              <CardDescription>
                Campaign create can call the backend mock API. Research, RAG, draft generation, review, mock send, follow-up, export, enrichment, scraping, and provider actions remain disabled.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="passed" label="Backend mock create" />
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No provider calls" />
        </CardContent>
      </Card>

      <CampaignBuilderShell />
    </section>
  );
}
