import { KeyRound, Lock, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";

const items = [
  { label: "Authentication boundary", state: "passed" as const, note: "Secure identity provider configuration active." },
  { label: "JWT verifier", state: "passed" as const, note: "Token verification and session validation active." },
  { label: "MFA enforcement", state: "passed" as const, note: "Multi-factor authentication enforced for privileged roles." },
  { label: "Support access audit", state: "passed" as const, note: "Support session audit logging active." },
];

export function SecurityPanel() {
  return (
    <BentoCard title="Security posture" description="Manage security posture, auth tokens, and session rules." badge="Secured">
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
          <Button><KeyRound className="size-4" /> Rotate session tokens</Button>
          <Button variant="secondary"><Lock className="size-4" /> Enforce MFA</Button>
        </div>
      </div>
    </BentoCard>
  );
}
