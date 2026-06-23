import { Brain, DatabaseZap, Search, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { ResearchArtifactCard } from "./research-artifact-card";
import { KnowledgeChunkCard } from "./knowledge-chunk-card";
import { SourceTrustPanel } from "./source-trust-panel";

export function ResearchWorkbench() {
  return (
    <div className="space-y-4">
      <BentoCard title="Research/RAG workbench" description="Local/demo research artifacts only. Backend agents, scrapers, embeddings, and enrichment providers are not called." badge="Local shell">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ResearchArtifactCard title="Campaign signal brief" description="Static approved context for frontend review." state="passed" />
          <ResearchArtifactCard title="Prospect fit notes" description="Demo artifact. No provider enrichment used." state="pending" />
          <ResearchArtifactCard title="Prompt-injection scan" description="UI shows local gate state only." state="passed" />
          <ResearchArtifactCard title="Live scraping" description="Disabled until approved backend route exists." state="blocked" />
        </div>
      </BentoCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <BentoCard title="Grounding context" description="Knowledge chunks displayed from local sample data only." badge="RAG preview">
          <div className="space-y-3">
            <KnowledgeChunkCard
              title="CRE owner outreach playbook"
              source="local chunk"
              excerpt="Use conservative claims, cite approved evidence, and require human review before mock send flows."
            />
            <KnowledgeChunkCard
              title="Grounded claims policy"
              source="local policy"
              excerpt="Claims without evidence must be blocked or marked needs_regeneration. Suppressed contacts block approval."
            />
          </div>
        </BentoCard>
        <SourceTrustPanel />
      </div>

      <BentoCard title="Gate result preview" description="These statuses mirror the safety UX only; backend remains the source of truth." badge="Review gates">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Search className="size-4 text-blue" /> Research queue
            </div>
            <GateReasonBadge state="pending" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Brain className="size-4 text-violet" /> Embeddings provider
            </div>
            <GateReasonBadge state="blocked" label="Disabled" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ShieldCheck className="size-4 text-green" /> Source trust
            </div>
            <GateReasonBadge state="warning" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <DatabaseZap className="size-4 text-yellow" /> Citation validation
            </div>
            <GateReasonBadge state="pending" className="mt-3" />
          </div>
        </div>
      </BentoCard>
    </div>
  );
}
