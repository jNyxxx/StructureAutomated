import Link from "next/link";
import { AlertTriangle, Database, Upload } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { ProspectsTable } from "@/components/prospects/prospects-table";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ProspectsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Prospect command center"
        title="Prospects"
        description="Read-only prospect workspace using backend mock API data with fixture fallback. Import, enrichment, campaign, export, and delete actions remain locked."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Button asChild variant="secondary">
              <Link href="/prospects/import">
                <Upload className="size-4" /> Import CSV shell
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
                This page only calls read-side backend mock APIs. Fixture fallback is local/mock, and all mutating actions stay locked.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="passed" label="Prospect API read-only" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No real enrichment" />
          <GateReasonBadge state="blocked" label="No real sending" />
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Read-only rows</CardTitle>
            <CardDescription>Backend mock API or fixture fallback only; no real provider data.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 text-h2 text-text">
              <Database className="size-5 text-blue" /> 4
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Compliance warnings</CardTitle>
            <CardDescription>Suppressed/duplicate/needs-review states block outreach.</CardDescription>
          </CardHeader>
          <CardContent>
            <GateReasonBadge state="warning" label="Review before outreach" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Campaign readiness</CardTitle>
            <CardDescription>Campaign assignment, send, export, and enrichment actions remain disabled.</CardDescription>
          </CardHeader>
          <CardContent>
            <GateReasonBadge state="pending" label="Actions locked" />
          </CardContent>
        </Card>
      </div>

      <ProspectsTable />
    </section>
  );
}
