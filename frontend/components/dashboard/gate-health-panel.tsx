import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

const gates = [
  { label: "Prompt injection fence", state: "passed" as const, note: "Backend foundation exists; UI remains read-only." },
  { label: "Source trust", state: "passed" as const, note: "Grounding checks stay backend-authoritative." },
  { label: "Groundedness", state: "passed" as const, note: "Current drafts still need API-backed review pages." },
  { label: "Human review", state: "pending" as const, note: "Review queue APIs are not mounted yet." },
  { label: "Send gate", state: "blocked" as const, note: "No real sending; mock flow only after backend wiring." },
];

export function GateHealthPanel() {
  return (
    <BentoCard title="Gate health" description="Safety gate overview using demo-safe local state." badge="No-send safe">
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
