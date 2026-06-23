import type { ReactNode } from "react";

import { FilterBar } from "./filter-bar";
import { SearchInput } from "./search-input";
import type { DataTableFilter } from "./types";

export function DataTableToolbar({
  search,
  onSearchChange,
  filters,
  onRemoveFilter,
  onClearFilters,
  children,
}: {
  search: string;
  onSearchChange: (value: string) => void;
  filters: DataTableFilter[];
  onRemoveFilter?: (key: string) => void;
  onClearFilters?: () => void;
  children?: ReactNode;
}) {
  return (
    <div className="space-y-3 border-b border-border p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput value={search} onChange={onSearchChange} />
        {children ? <div className="flex flex-wrap gap-2">{children}</div> : null}
      </div>
      <FilterBar filters={filters} onRemove={onRemoveFilter} onClear={onClearFilters} />
    </div>
  );
}
