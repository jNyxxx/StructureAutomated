import { BarChart3, CheckCircle2, FileText, MailCheck, Search, Send, ShieldCheck, Sparkles, Upload, Users } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

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
          const iconToneClass = {
            passed: "bg-goodbg text-green shadow-[0_0_10px_rgba(34,197,94,0.25)] ring-1 ring-green/20",
            warning: "bg-warnbg text-yellow shadow-[0_0_10px_rgba(245,158,11,0.25)] ring-1 ring-yellow/20",
            failed: "bg-redbg text-red shadow-[0_0_10px_rgba(239,68,68,0.25)] ring-1 ring-red/20",
            missing: "bg-transparent text-muted ring-1 ring-border",
            denied: "bg-redbg text-red shadow-[0_0_10px_rgba(239,68,68,0.25)] ring-1 ring-red/20",
            blocked: "bg-panel2 text-muted/60 ring-1 ring-border/50",
            pending: "bg-bluebg/40 text-blue/70 ring-1 ring-blue/10",
          }[step.state];

          return (
            <Card key={step.label} className="p-3.5 transition-all duration-300 hover:border-blue/50">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className={cn("flex size-9 items-center justify-center rounded-small transition-all duration-300", iconToneClass)}>
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
            </Card>
          );
        })}
      </div>
    </BentoCard>
  );
}
