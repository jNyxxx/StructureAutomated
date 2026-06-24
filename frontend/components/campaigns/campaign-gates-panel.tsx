import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const gates = [
  { label: "Research/RAG settings", state: "pending" as const, note: "Workbench route is deferred." },
  { label: "Draft rules", state: "pending" as const, note: "Draft generation API is not mounted." },
  { label: "Human approval", state: "blocked" as const, note: "Approve action remains locked." },
  { label: "Send gate", state: "blocked" as const, note: "No real sending in local/mock MVP." },
  { label: "Billing/access gate", state: "blocked" as const, note: "Central backend gate required." },
];

export function CampaignGatesPanel() {
  return (
    <BentoCard title="Safety and review gates" description="Campaign mutations stay disabled until backend APIs exist." badge="Locked">
      <div className="space-y-3">
        {gates.map((gate) => (
          <div key={gate.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-small font-semibold text-text">{gate.label}</p>
              <GateReasonBadge state={gate.state} />
            </div>
            <p className="mt-2 text-caption text-muted">{gate.note}</p>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
