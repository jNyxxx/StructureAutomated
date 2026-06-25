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
        description="Local/mock CSV import flow using the backend mock API. No live scraping, enrichment, campaign assignment, provider calls, real sending, or production import is enabled."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="default">Backend mock import</Badge>
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
              <CardTitle>Safe local/mock import only</CardTitle>
              <CardDescription>
                CSV import now submits to the backend mock API only. Enrichment, live scraping, campaign assignment, export, delete, and send actions remain disabled.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="passed" label="Backend mock API" />
          <GateReasonBadge state="blocked" label="No real enrichment" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No real sending" />
        </CardContent>
      </Card>

      <CsvImportWizard />
    </section>
  );
}
