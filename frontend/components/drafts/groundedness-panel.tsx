import { ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { ClaimHighlighter } from "./claim-highlighter";
import { EvidenceList } from "./evidence-list";
import type { DraftRow } from "./draft-sample-data";

export function GroundednessPanel({ draft }: { draft: DraftRow }) {
  return (
    <BentoCard title="Groundedness and citations" description="Read-only local/mock evidence panel. No embeddings provider or live scraper is called." badge="Grounding shell">
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="text-caption text-subtle">Groundedness gate</p>
            <GateReasonBadge state={draft.groundednessGate} className="mt-2" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="text-caption text-subtle">Evidence cards</p>
            <p className="mt-1 text-h3 text-text">{draft.evidence.length}</p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="text-caption text-subtle">Unsupported claims</p>
            <p className="mt-1 text-h3 text-text">{draft.unsupportedClaims.length}</p>
          </div>
        </div>
        <ClaimHighlighter claims={draft.unsupportedClaims} />
        <div>
          <div className="mb-3 flex items-center gap-2 text-small font-semibold text-text">
            <ShieldCheck className="size-4 text-blue" /> Evidence/source list
          </div>
          <EvidenceList evidence={draft.evidence} />
        </div>
      </div>
    </BentoCard>
  );
}
