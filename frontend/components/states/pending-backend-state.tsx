import { PlugZap } from "lucide-react";
import type { ReactNode } from "react";

import { GateReasonBadge } from "@/components/badges";

import { StateShell } from "./state-shell";

export function PendingBackendState({
  title = "Pending backend API",
  description = "This UI route is available for design validation, but the matching HTTP API is not mounted yet. Actions remain locked.",
  primaryAction,
  secondaryAction,
}: {
  title?: string;
  description?: string;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
}) {
  return (
    <StateShell
      title={title}
      description={description}
      icon={PlugZap}
      tone="pending"
      primaryAction={primaryAction}
      secondaryAction={secondaryAction}
    >
      <div className="flex flex-wrap gap-2">
        <GateReasonBadge state="pending" label="API not mounted" />
        <GateReasonBadge state="blocked" label="Actions locked" />
        <GateReasonBadge state="missing" label="No wiring yet" />
      </div>
    </StateShell>
  );
}
