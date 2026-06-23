import { Clock3, ScrollText, ShieldCheck } from "lucide-react";

import { StatusBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const activity = [
  { label: "P1-13 evidence recorded", meta: "redacted local evidence", status: "approved" as const },
  { label: "Frontend route shell opened", meta: "request_id hidden in demo", status: "pending_review" as const },
  { label: "Mock send action blocked", meta: "send gate pending backend API", status: "blocked" as const },
];

export function ActivityPreview() {
  return (
    <BentoCard title="Activity / audit preview" description="Redacted demo-safe events only; no secrets or raw contact data." badge="Redacted">
      <div className="space-y-3">
        {activity.map((item) => (
          <div key={item.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <ScrollText className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{item.label}</p>
                  <p className="text-caption text-muted">{item.meta}</p>
                </div>
              </div>
              <StatusBadge status={item.status} />
            </div>
          </div>
        ))}
        <div className="flex items-center gap-2 rounded-medium border border-green/25 bg-goodbg p-3 text-caption text-muted">
          <ShieldCheck className="size-4 text-green" /> Audit preview uses safe, redacted local copy only.
        </div>
        <div className="flex items-center gap-2 text-caption text-subtle">
          <Clock3 className="size-3.5" /> Live audit API is not wired in this frontend slice.
        </div>
      </div>
    </BentoCard>
  );
}
