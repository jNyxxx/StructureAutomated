import { AlertTriangle, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { ReviewQueueTable } from "@/components/review/review-queue-table";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ReviewQueuePage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Human review gate"
        title="Review queue"
        description="Demo-safe review workspace using local rows only. Approval, rejection, regeneration, edits, mock send, follow-up, and export APIs are not mounted yet."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Button disabled>
              <ShieldCheck className="size-4" /> Bulk approve locked
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
                Human approval never bypasses safety, groundedness, suppression, billing, throttles, deliverability, or send gates. This page does not mutate backend data.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="pending" label="Review API pending" />
          <GateReasonBadge state="blocked" label="No real sending" />
          <GateReasonBadge state="blocked" label="No provider calls" />
          <GateReasonBadge state="blocked" label="No live scraping" />
          <GateReasonBadge state="blocked" label="No Stripe/SMS/webhooks" />
        </CardContent>
      </Card>

      <ReviewQueueTable />
    </section>
  );
}
