import { ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { privacyPosture } from "./privacy-sample-data";

export function PrivacyPostureCard() {
  return (
    <BentoCard title="Privacy posture" description="Frontend privacy posture shell only. Backend privacy workflows are pending." badge="Privacy shell">
      <div className="grid gap-3 md:grid-cols-2">
        {privacyPosture.map((item) => (
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
      </div>
    </BentoCard>
  );
}
