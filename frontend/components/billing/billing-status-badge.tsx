import { AlertTriangle, CheckCircle2, Clock3, Lock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { MockBillingState } from "./billing-sample-data";

export function BillingStatusBadge({ state }: { state: MockBillingState }) {
  const config = {
    trialing: { label: "Trialing", variant: "default" as const, icon: Clock3 },
    active: { label: "Active", variant: "success" as const, icon: CheckCircle2 },
    past_due: { label: "Past due", variant: "warning" as const, icon: AlertTriangle },
    canceled: { label: "Canceled", variant: "locked" as const, icon: Lock },
    unpaid: { label: "Unpaid", variant: "danger" as const, icon: AlertTriangle },
    inactive: { label: "Inactive", variant: "locked" as const, icon: Lock },
  }[state];
  const Icon = config.icon;
  return (
    <Badge variant={config.variant} className="gap-1.5">
      <Icon className="size-3.5" /> {config.label}
    </Badge>
  );
}
