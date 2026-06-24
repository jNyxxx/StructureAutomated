import Link from "next/link";
import { ArrowLeft, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { CsvImportWizard } from "@/components/import/csv-import-wizard";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ProspectImportPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="CSV import wizard"
        title="Import prospects"
        description="Visual-only CSV import flow with sample local rows. No files are uploaded, persisted, enriched, scraped, or sent."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Import API pending</Badge>
            <Button asChild variant="secondary">
              <Link href="/prospects">
                <ArrowLeft className="size-4" /> Back to prospects
              </Link>
            </Button>
          </>
        }
      />

      <LocalMockNotice />

      <Card className="border-red/25 bg-redbg/50">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-redbg text-red">
              <ShieldAlert className="size-5" />
            </div>
            <div>
              <CardTitle>Import confirmation is locked</CardTitle>
              <CardDescription>
                Backend import, validation persistence, enrichment, live scraping, and campaign assignment routes are not mounted. Suppression/compliance warnings must block outreach actions.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="blocked" label="No backend upload" />
          <GateReasonBadge state="blocked" label="No real enrichment" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No real sending" />
        </CardContent>
      </Card>

      <CsvImportWizard />
    </section>
  );
}
