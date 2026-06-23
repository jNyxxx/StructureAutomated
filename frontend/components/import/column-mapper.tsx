import { ArrowRight, Columns3 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { suggestedColumnMapping } from "./sample-import-data";

export function ColumnMapper() {
  return (
    <div className="rounded-xl border border-border bg-panel p-5 shadow-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <Columns3 className="size-4 text-blue" /> Column mapping
          </div>
          <p className="mt-1 text-small text-muted">Suggested local/demo mappings only. Nothing is persisted.</p>
        </div>
        <GateReasonBadge state="pending" label="Mapping API pending" />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {suggestedColumnMapping.map((item) => (
          <div key={item.source} className="flex items-center gap-3 rounded-medium border border-border bg-panel2 p-3 text-small">
            <span className="rounded-small bg-panel px-2 py-1 text-muted">{item.source}</span>
            <ArrowRight className="size-4 text-subtle" />
            <span className="font-semibold text-text">{item.target}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
