import { CalendarClock, MailCheck, Send } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import type { ReviewItem } from "./review-sample-data";

export function SendReadinessPanel({ item }: { item: ReviewItem }) {
  return (
    <BentoCard title="Send gate readiness" description="Send and follow-up actions stay disabled. Approval cannot bypass send gates." badge="No-send">
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <MailCheck className="size-4 text-yellow" /> Send readiness
            </div>
            <GateReasonBadge state={item.sendReadiness} label="Locked" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Send className="size-4 text-red" /> Mock send
            </div>
            <GateReasonBadge state="blocked" label="Pending backend" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CalendarClock className="size-4 text-blue" /> Follow-up
            </div>
            <GateReasonBadge state="blocked" label="Schedule locked" className="mt-3" />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled>
            <Send className="size-4" /> Mock send
          </Button>
          <Button disabled variant="secondary">
            <CalendarClock className="size-4" /> Schedule follow-up
          </Button>
          <Button disabled variant="locked">
            Export locked
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
