import { AlertTriangle, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { ReviewQueueTable } from "@/components/review/review-queue-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ReviewQueuePage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Human review gate"
        title="Review queue"
        description="Approve or edit outreach drafts before sending."
        actions={<Button disabled>
              <ShieldCheck className="size-4" /> Bulk approve locked
            </Button>}
      />

      <ReviewQueueTable />
    </section>
  );
}
