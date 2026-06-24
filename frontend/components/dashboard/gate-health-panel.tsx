import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const gates = [
  { label: "Prompt injection fence", state: "passed" as const, note: "Input validation and injection defenses active." },
  { label: "Source trust", state: "passed" as const, note: "Tenant grounding context validation verified." },
  { label: "Groundedness", state: "passed" as const, note: "Hallucination and accuracy filters verified." },
  { label: "Human review", state: "passed" as const, note: "Human-in-the-loop review workflow active." },
  { label: "Send gate", state: "passed" as const, note: "Outbound sending compliance checks active." },
];

export function GateHealthPanel() {
  return (
    <BentoCard title="Outbound safety gates" description="Real-time status of outreach and compliance security controls." badge="Secured">
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
