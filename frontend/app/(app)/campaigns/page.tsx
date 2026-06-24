import Link from "next/link";
import { AlertTriangle, Plus } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { CampaignsTable } from "@/components/campaigns/campaigns-table";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function CampaignsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign command center"
        title="Campaigns"
        description="Demo-safe campaign workspace using local rows only. Campaign creation, research, drafts, review, send, follow-up, and export APIs are not mounted yet."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Button asChild variant="secondary">
              <Link href="/campaigns/new">
                <Plus className="size-4" /> New campaign shell
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
              <CardTitle>Pending backend API notice</CardTitle>
              <CardDescription>
                This page does not call unavailable campaign APIs. All rows are local/demo and every mutating action stays locked.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="pending" label="Campaign API pending" />
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No provider calls" />
          <GateReasonBadge state="blocked" label="No production" />
        </CardContent>
      </Card>

      <CampaignsTable />
    </section>
  );
}
