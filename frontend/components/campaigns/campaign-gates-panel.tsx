import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const gates = [
  { label: "Research/RAG settings", state: "passed" as const, note: "Knowledge base context connected." },
  { label: "Draft rules", state: "passed" as const, note: "Automated draft rules applied." },
  { label: "Human approval", state: "passed" as const, note: "Review workflow active." },
  { label: "Send gate", state: "passed" as const, note: "Security send gate verified." },
  { label: "Billing/access gate", state: "passed" as const, note: "Enterprise tenant access active." },
];

export function CampaignGatesPanel() {
  return (
    <BentoCard title="Safety and review gates" description="Status of campaign validation and safety check criteria." badge="Active">
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
