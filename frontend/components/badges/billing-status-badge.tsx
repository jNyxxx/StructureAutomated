import { AlertTriangle, CircleCheck, CircleSlash, Clock3, CreditCard, Lock } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type BillingBadgeState = "trialing" | "active" | "past_due" | "canceled" | "unpaid" | "inactive";

const billingConfig: Record<
  BillingBadgeState,
  { label: string; variant: BadgeProps["variant"]; icon: typeof CircleCheck }
> = {
  trialing: { label: "Trialing", variant: "default", icon: Clock3 },
  active: { label: "Active", variant: "success", icon: CircleCheck },
  past_due: { label: "Past due", variant: "warning", icon: AlertTriangle },
  canceled: { label: "Canceled", variant: "locked", icon: CircleSlash },
  unpaid: { label: "Unpaid", variant: "danger", icon: CreditCard },
  inactive: { label: "Inactive", variant: "locked", icon: Lock },
};

export function BillingStatusBadge({
  state,
  className,
}: {
  state: BillingBadgeState;
  className?: string;
}) {
  const config = billingConfig[state];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn("gap-1.5", className)}>
      <Icon className="size-3.5" />
      {config.label}
    </Badge>
  );
}
