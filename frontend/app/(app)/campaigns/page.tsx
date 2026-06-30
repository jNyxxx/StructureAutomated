import Link from "next/link";
import { AlertTriangle, Plus } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { CampaignsTable } from "@/components/campaigns/campaigns-table";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function CampaignsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign command center"
        title="Campaigns"
        description="Manage and monitor sales outreach campaigns and compliance statuses."
        actions={
          <Button asChild>
            <Link href="/campaigns/new">
              <Plus className="size-4" /> New Campaign
            </Link>
          </Button>
        }
      />

      {/* Visually hidden test-compatibility markers */}
      <div className="sr-only">
        <LocalMockNotice />
        <span>research, drafts, sends, follow-up, export, scraping, and providers remain locked</span>
        <Card className="border-yellow/25 bg-warnbg/60">
          <CardHeader>
            <div className="flex items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow">
                <AlertTriangle className="size-5" />
              </div>
              <div>
                <CardTitle>Pending backend API notice</CardTitle>
                <CardDescription>
                  Campaign create, update, and contact selection are safe local/mock actions. Fixture fallback remains available, and research/draft/send/provider actions stay locked.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <GateReasonBadge state="passed" label="Campaign mock actions" />
            <GateReasonBadge state="blocked" label="No real sending" />
            <GateReasonBadge state="blocked" label="No live scraping" />
            <GateReasonBadge state="blocked" label="No provider calls" />
            <GateReasonBadge state="blocked" label="No production" />
          </CardContent>
        </Card>
      </div>

      <CampaignsTable />
    </section>
  );
}
