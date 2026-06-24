import Link from "next/link";
import { AlertTriangle, Database, Upload } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { ProspectsTable } from "@/components/prospects/prospects-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ProspectsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Prospect command center"
        title="Prospects"
        description="View and manage prospective contacts and leads."
        actions={<Button asChild variant="secondary">
              <Link href="/prospects/import">
                <Upload className="size-4" /> Import CSV shell
              </Link>
            </Button>}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Local rows</CardTitle>
            <CardDescription>Demo-only contacts, no real emails or provider data.</CardDescription>
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
            <CardDescription>Campaign APIs are still unavailable in this frontend slice.</CardDescription>
          </CardHeader>
          <CardContent>
            <GateReasonBadge state="pending" label="Pending backend" />
          </CardContent>
        </Card>
      </div>

      <ProspectsTable />
    </section>
  );
}
