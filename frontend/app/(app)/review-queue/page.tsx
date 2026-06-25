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
        description="Review workspace using backend mock API data with fixture fallback. Approve, reject, and request-regeneration are local/mock actions; send, send-gate, follow-up, outbound dispatch, and export remain locked."
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
              <CardTitle>Safe local/mock review actions only</CardTitle>
              <CardDescription>
                Human approval never bypasses safety, groundedness, suppression, billing, throttles, deliverability, or send gates. Approve, reject, and request-regeneration call backend mock APIs only; no live AI/provider/send action is enabled.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="passed" label="Review mock actions" />
          <GateReasonBadge state="passed" label="Review read refresh" />
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
