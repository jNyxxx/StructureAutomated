import { Clock3, ScrollText } from "lucide-react";

import { StatusBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import type { ReviewItem } from "./review-sample-data";

export function ReviewActivityTimeline({ item }: { item: ReviewItem }) {
  return (
    <BentoCard title="Review activity trail" description="Redacted local/demo audit trail. No live audit API is called." badge="Audit shell">
      <div className="space-y-3">
        {item.safeActivity.map((event, index) => (
          <div key={event} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <ScrollText className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{event}</p>
                  <p className="text-caption text-muted">local/demo event #{index + 1}</p>
                </div>
              </div>
              <StatusBadge status={index === 0 ? "pending_review" : "blocked"} />
            </div>
          </div>
        ))}
        <div className="flex items-center gap-2 text-caption text-subtle">
          <Clock3 className="size-3.5" /> Backend audit, approvals, and sends are not wired in this slice.
        </div>
      </div>
    </BentoCard>
  );
}
