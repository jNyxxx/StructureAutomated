import { Clock3 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { privacyTimeline } from "./privacy-sample-data";

export function PrivacyTimeline() {
  return (
    <BentoCard title="Request status timeline" description="Demo timeline only; no request status is persisted." badge="Timeline shell">
      <div className="space-y-3">
        {privacyTimeline.map((item) => (
          <div key={item.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue"><Clock3 className="size-4" /></div>
                <div>
                  <p className="text-small font-semibold text-text">{item.label}</p>
                  <p className="text-caption text-muted">{item.detail}</p>
                </div>
              </div>
              <GateReasonBadge state={item.state} />
            </div>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
