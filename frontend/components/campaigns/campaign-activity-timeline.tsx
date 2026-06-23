import { Clock3, ScrollText } from "lucide-react";

import { StatusBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const events = [
  { label: "Campaign shell opened", meta: "local/demo route", status: "pending_review" as const },
  { label: "Send gate evaluated", meta: "blocked: no real sending", status: "blocked" as const },
  { label: "Export requested", meta: "blocked: export API pending", status: "blocked" as const },
];

export function CampaignActivityTimeline() {
  return (
    <BentoCard title="Activity timeline" description="Redacted demo-safe campaign events only." badge="Shell">
      <div className="space-y-3">
        {events.map((event) => (
          <div key={event.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <ScrollText className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{event.label}</p>
                  <p className="text-caption text-muted">{event.meta}</p>
                </div>
              </div>
              <StatusBadge status={event.status} />
            </div>
          </div>
        ))}
        <div className="flex items-center gap-2 text-caption text-subtle">
          <Clock3 className="size-3.5" /> No live audit/campaign API is called from this timeline.
        </div>
      </div>
    </BentoCard>
  );
}
