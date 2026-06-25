import { AlertTriangle, Sparkles } from "lucide-react";

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
        description="Read-only AI draft workspace using local/mock draft rows with backend mock API detail/evidence loading in the preview drawer. Generate, regenerate, approve, send, scraping, enrichment, and provider actions remain locked."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Button disabled>
              <Sparkles className="size-4" /> Generate locked
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
                This page only uses read-side draft detail/evidence backend mock APIs when a safe draft preview is opened. Generation, review, scraping, enrichment, provider, and send mutations stay locked.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="passed" label="Draft detail/evidence read-only" />
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
