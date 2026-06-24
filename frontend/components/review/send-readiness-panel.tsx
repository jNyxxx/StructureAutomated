import { CalendarClock, MailCheck, Send } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import type { ReviewItem } from "./review-sample-data";

export function SendReadinessPanel({ item }: { item: ReviewItem }) {
  return (
    <BentoCard title="Send gate readiness" description="Outbound outreach and schedule configuration status." badge="Ready">
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <MailCheck className="size-4 text-green" /> Send readiness
            </div>
            <GateReasonBadge state="passed" label="Verified" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Send className="size-4 text-green" /> Outbound send
            </div>
            <GateReasonBadge state="passed" label="Active" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CalendarClock className="size-4 text-blue" /> Follow-up
            </div>
            <GateReasonBadge state="passed" label="Active" className="mt-3" />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="default">
            <Send className="size-4" /> Send email
          </Button>
          <Button variant="secondary">
            <CalendarClock className="size-4" /> Schedule follow-up
          </Button>
          <Button variant="secondary">
            Export data
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
