import { CreditCard, Lock } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";

export function BillingLockBanner() {
  return (
    <div className="rounded-xl border border-yellow/30 bg-warnbg p-5 shadow-panel">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-warnbg text-yellow">
            <Lock className="size-5" />
          </div>
          <div>
            <p className="font-semibold text-text">Mock billing only — real Stripe deferred</p>
            <p className="mt-1 text-small text-muted">
              This MVP shows schema/access-state UX only. No checkout, webhooks, money movement, or customer portal is enabled.
            </p>
          </div>
        </div>
        <GateReasonBadge state="blocked" label="Stripe deferred" />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button disabled>
          <CreditCard className="size-4" /> Upgrade pending Stripe
        </Button>
        <Button disabled variant="secondary">Manage billing locked</Button>
      </div>
    </div>
  );
}
