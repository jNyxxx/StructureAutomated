import { BarChart3, CheckCircle2, FileText, MailCheck, Search, Send, ShieldCheck, Sparkles, Upload, Users } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const steps = [
  { label: "Import", icon: Upload, state: "pending" as const },
  { label: "Campaign", icon: Send, state: "pending" as const },
  { label: "Research", icon: Search, state: "pending" as const },
  { label: "RAG", icon: FileText, state: "pending" as const },
  { label: "Draft", icon: Sparkles, state: "pending" as const },
  { label: "Safety", icon: ShieldCheck, state: "passed" as const },
  { label: "Review", icon: Users, state: "pending" as const },
  { label: "Mock send", icon: MailCheck, state: "blocked" as const },
  { label: "Follow-up", icon: Send, state: "pending" as const },
  { label: "Deliverability", icon: ShieldCheck, state: "pending" as const },
  { label: "Outcomes", icon: BarChart3, state: "pending" as const },
];

export function FlowProgress() {
  return (
    <BentoCard
      title="MVP flow progress"
      description="Demo-safe command flow. Product APIs are not mounted in the frontend yet."
      badge="Local/mock"
      className="xl:col-span-2"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.label} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                    <Icon className="size-4" />
                  </div>
                  <div>
                    <p className="text-caption text-subtle">Step {index + 1}</p>
                    <p className="text-small font-semibold text-text">{step.label}</p>
                  </div>
                </div>
                {step.state === "passed" ? <CheckCircle2 className="size-4 text-green" /> : null}
              </div>
              <GateReasonBadge state={step.state} className="mt-3" />
            </div>
          );
        })}
      </div>
    </BentoCard>
  );
}
