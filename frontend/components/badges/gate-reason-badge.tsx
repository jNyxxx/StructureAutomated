import { CheckCircle2, CircleAlert, CircleDashed, CircleX, Lock, ShieldAlert } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type GateState = "passed" | "warning" | "failed" | "missing" | "denied" | "blocked" | "pending";

const gateConfig: Record<GateState, { label: string; variant: BadgeProps["variant"]; icon: typeof CheckCircle2 }> = {
  passed: { label: "Passed", variant: "success", icon: CheckCircle2 },
  warning: { label: "Warning", variant: "warning", icon: CircleAlert },
  failed: { label: "Failed", variant: "danger", icon: CircleX },
  missing: { label: "Missing", variant: "outline", icon: CircleDashed },
  denied: { label: "Denied", variant: "danger", icon: ShieldAlert },
  blocked: { label: "Blocked", variant: "locked", icon: Lock },
  pending: { label: "Pending", variant: "warning", icon: CircleDashed },
};

export function GateReasonBadge({
  state,
  label,
  className,
}: {
  state: GateState;
  label?: string;
  className?: string;
}) {
  const config = gateConfig[state];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn("gap-1.5", className)}>
      <Icon className="size-3.5" />
      {label ?? config.label}
    </Badge>
  );
}
