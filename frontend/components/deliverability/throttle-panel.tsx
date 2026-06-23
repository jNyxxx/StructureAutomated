import { Gauge, Lock } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";

export function ThrottlePanel() {
  return (
    <BentoCard title="Throttle controls" description="Read-only throttling shell. Backend send throttle APIs are not mounted." badge="Locked">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <Gauge className="size-4 text-blue" /> Daily cap
          </div>
          <p className="mt-2 text-h3 text-text">25</p>
          <p className="text-caption text-muted">demo cap only</p>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <Gauge className="size-4 text-yellow" /> Per-hour cap
          </div>
          <p className="mt-2 text-h3 text-text">5</p>
          <p className="text-caption text-muted">preview only</p>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <Lock className="size-4 text-red" /> Real send
          </div>
          <GateReasonBadge state="blocked" label="Disabled" className="mt-3" />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button disabled>
          <Lock className="size-4" /> Update throttle
        </Button>
        <Button disabled variant="secondary">Pause sending</Button>
      </div>
    </BentoCard>
  );
}
