import { BarChart3, MailCheck, ShieldCheck, TrendingUp } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const items = [
  { title: "Mailbox health", icon: MailCheck, note: "Preview only; provider APIs are not wired." },
  { title: "Domain safety", icon: ShieldCheck, note: "DNS/provider checks are deferred." },
  { title: "Reply outcomes", icon: TrendingUp, note: "Outcomes API pending." },
  { title: "ROI visibility", icon: BarChart3, note: "Demo-safe shell only." },
];

export function DeliverabilityOutcomesPreview() {
  return (
    <BentoCard title="Deliverability / outcomes preview" description="Visibility panels without provider calls, real sending, or outcome API wiring." badge="Preview">
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.title} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-violetbg text-violet">
                  <Icon className="size-4" />
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{item.title}</p>
                  <p className="text-caption text-muted">{item.note}</p>
                </div>
              </div>
              <GateReasonBadge state="pending" label="Pending backend" className="mt-3" />
            </div>
          );
        })}
      </div>
    </BentoCard>
  );
}
