import { CreditCard } from "lucide-react";
import type { ReactNode } from "react";

import { BillingStatusBadge, type BillingBadgeState } from "@/components/badges";

import { StateShell } from "./state-shell";

export function BillingLockedState({
  state = "inactive",
  title = "Billing locked",
  description = "This tenant is not allowed to perform costly or outbound actions. Mock MVP billing gates stay locked until the backend confirms access.",
  primaryAction,
  secondaryAction,
}: {
  state?: BillingBadgeState;
  title?: string;
  description?: string;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
}) {
  return (
    <StateShell
      title={title}
      description={description}
      icon={CreditCard}
      tone="warning"
      primaryAction={primaryAction}
      secondaryAction={secondaryAction}
    >
      <BillingStatusBadge state={state} />
    </StateShell>
  );
}
