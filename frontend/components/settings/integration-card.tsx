import { Lock, PlugZap } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";

export function IntegrationCard({ name, description, status, phase }: { name: string; description: string; status: string; phase: string }) {
  const state = status === "Connected" ? "passed" : "pending";
  return (
    <div className="rounded-xl border border-border bg-panel p-5 shadow-panel">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-violetbg text-violet">
            <PlugZap className="size-5" />
          </div>
          <div>
            <p className="font-semibold text-text">{name}</p>
            <p className="mt-1 text-small text-muted">{description}</p>
            <p className="mt-2 text-caption text-subtle">Status: Active</p>
          </div>
        </div>
        <GateReasonBadge state={state} label={status} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="secondary">
          Configure
        </Button>
      </div>
    </div>
  );
}
