import { Database, Link2 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import type { EvidenceItem } from "./draft-sample-data";

export function EvidenceList({ evidence }: { evidence: EvidenceItem[] }) {
  if (evidence.length === 0) {
    return (
      <div className="rounded-medium border border-border bg-panel2 p-3 text-small text-muted">
        No approved evidence attached. Groundedness cannot pass without backend-validated sources.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {evidence.map((item) => (
        <div key={item.id} className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex gap-3">
              <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                <Database className="size-4" />
              </div>
              <div>
                <p className="text-small font-semibold text-text">{item.title}</p>
                <p className="mt-1 flex items-center gap-1 text-caption text-subtle">
                  <Link2 className="size-3.5" /> {item.source}
                </p>
              </div>
            </div>
            <GateReasonBadge state={item.trust} />
          </div>
          <p className="mt-3 text-small text-muted">{item.excerpt}</p>
        </div>
      ))}
    </div>
  );
}
