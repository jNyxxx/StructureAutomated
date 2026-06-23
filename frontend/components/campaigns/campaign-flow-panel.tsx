import { BarChart3, Clock3, FileText, MailCheck, Search, Send, ShieldCheck, Sparkles, Users } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const stages = [
  { label: "Prospects", icon: Users, state: "passed" as const },
  { label: "Research", icon: Search, state: "pending" as const },
  { label: "RAG", icon: FileText, state: "pending" as const },
  { label: "Drafts", icon: Sparkles, state: "pending" as const },
  { label: "Review", icon: ShieldCheck, state: "pending" as const },
  { label: "Send gate", icon: MailCheck, state: "blocked" as const },
  { label: "Follow-up", icon: Clock3, state: "blocked" as const },
  { label: "Outcomes", icon: BarChart3, state: "pending" as const },
];

export function CampaignFlowPanel() {
  return (
    <BentoCard title="Pipeline stage progress" description="Visual-only campaign pipeline. No backend campaign APIs are called." badge="Demo flow">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {stages.map((stage) => {
          const Icon = stage.icon;
          return (
            <div key={stage.label} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  <Icon className="size-4" />
                </div>
                <p className="text-small font-semibold text-text">{stage.label}</p>
              </div>
              <GateReasonBadge state={stage.state} className="mt-3" />
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex items-center gap-2 text-caption text-subtle">
        <Send className="size-3.5" /> Mock send remains locked until actual backend APIs exist.
      </div>
    </BentoCard>
  );
}
