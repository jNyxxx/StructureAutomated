import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DraftsTable } from "@/components/drafts/drafts-table";
import { ResearchWorkbench } from "@/components/research/research-workbench";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AiDraftsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Research/RAG and draft review"
        title="AI drafts"
        description="Local/mock AI draft workspace using backend mock draft generation plus detail/evidence loading. Regenerate, review approval, send, scraping, enrichment, and provider actions remain locked."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Button disabled>
              Review/send locked
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
              <CardTitle>Safe local/mock draft generation only</CardTitle>
              <CardDescription>
                Draft generation can call the backend mock API. Regeneration, review, scraping, enrichment, provider, and send mutations stay locked.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="passed" label="Draft generation mock" />
          <GateReasonBadge state="passed" label="Draft detail/evidence reload" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No provider enrichment" />
          <GateReasonBadge state="blocked" label="No embeddings provider" />
          <GateReasonBadge state="blocked" label="No real sending" />
        </CardContent>
      </Card>

      <DraftsTable />
      <ResearchWorkbench />
    </section>
  );
}
