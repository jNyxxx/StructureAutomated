import { KeyRound, Lock, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";

const items = [
  { label: "Clerk/local mock boundary", state: "warning" as const, note: "Frontend shell uses local/mock auth boundary language for MVP demos." },
  { label: "Production JWT verifier", state: "pending" as const, note: "Backend production verifier remains pending for production launch." },
  { label: "MFA requirement", state: "warning" as const, note: "MFA status is displayed only; backend enforcement is source of truth." },
  { label: "Support access audit", state: "pending" as const, note: "Support access must be audited before production." },
];

export function SecurityPanel() {
  return (
    <BentoCard title="Security posture" description="Auth/session/MFA shell only. No backend security mutation APIs are called." badge="Security shell">
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <ShieldCheck className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{item.label}</p>
                  <p className="text-caption text-muted">{item.note}</p>
                </div>
              </div>
              <GateReasonBadge state={item.state} />
            </div>
          </div>
        ))}
        <div className="flex flex-wrap gap-2 pt-2">
          <Button disabled><KeyRound className="size-4" /> Rotate session locked</Button>
          <Button disabled variant="secondary"><Lock className="size-4" /> Enforce MFA pending</Button>
        </div>
      </div>
    </BentoCard>
  );
}
