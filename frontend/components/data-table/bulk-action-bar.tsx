import { Download, Lock, Trash2 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";

export function BulkActionBar({ selectedCount, onClear }: { selectedCount: number; onClear: () => void }) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-blue/25 bg-bluebg/60 p-3 text-small text-muted shadow-panel sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-text">{selectedCount} selected</span>
        <GateReasonBadge state="blocked" label="Bulk API pending" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" size="sm" disabled>
          <Download className="size-4" /> Export
        </Button>
        <Button type="button" variant="secondary" size="sm" disabled>
          <Trash2 className="size-4" /> Delete
        </Button>
        <Button type="button" variant="locked" size="sm" disabled>
          <Lock className="size-4" /> Locked
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onClear}>
          Clear
        </Button>
      </div>
    </div>
  );
}
