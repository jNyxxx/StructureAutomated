import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { DataTableSortDirection } from "./types";

export function DataTableColumnHeader({
  label,
  sortable,
  direction,
  onSort,
}: {
  label: string;
  sortable?: boolean;
  direction?: DataTableSortDirection | null;
  onSort?: () => void;
}) {
  if (!sortable) {
    return <span>{label}</span>;
  }

  const Icon = direction === "asc" ? ArrowUp : direction === "desc" ? ArrowDown : ChevronsUpDown;

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="-ml-2 h-8 gap-1.5 px-2 text-caption uppercase tracking-wide text-muted"
      onClick={onSort}
      aria-label={`Sort by ${label}`}
      aria-sort={direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none"}
    >
      {label}
      <Icon className="size-3.5" />
    </Button>
  );
}
