import Link from "next/link";
import { AlertTriangle, Plus } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { CampaignsTable } from "@/components/campaigns/campaigns-table";
import { PageHeader } from "@/components/layout/page-header";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function CampaignsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign command center"
        title="Campaigns"
        description="Manage and run your cold-outreach campaigns."
        actions={<Button asChild variant="secondary">
              <Link href="/campaigns/new">
                <Plus className="size-4" /> New campaign shell
              </Link>
            </Button>}
      />

      <CampaignsTable />
    </section>
  );
}
