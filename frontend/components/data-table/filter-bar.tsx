import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { DataTableFilter } from "./types";

export function FilterBar({
  filters,
  onRemove,
  onClear,
}: {
  filters: DataTableFilter[];
  onRemove?: (key: string) => void;
  onClear?: () => void;
}) {
  if (filters.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Active filters">
      {filters.map((filter) => (
        <Badge key={filter.key} variant="outline" className="gap-1.5">
          {filter.label}: {filter.value}
          {onRemove ? (
            <button
              type="button"
              className="rounded-pill text-subtle hover:text-text focus:outline-none focus:ring-2 focus:ring-blue"
              onClick={() => onRemove(filter.key)}
              aria-label={`Remove ${filter.label} filter`}
            >
              <X className="size-3" />
            </button>
          ) : null}
        </Badge>
      ))}
      {onClear ? (
        <Button variant="ghost" size="sm" onClick={onClear}>
          Clear filters
        </Button>
      ) : null}
    </div>
  );
}
