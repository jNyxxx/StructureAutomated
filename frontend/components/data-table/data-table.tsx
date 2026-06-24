"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";

import { BulkActionBar } from "./bulk-action-bar";
import { DataTableColumnHeader } from "./data-table-column-header";
import { DataTableEmptyState } from "./data-table-empty-state";
import { DataTableLoadingState } from "./data-table-loading-state";
import { DataTablePagination } from "./data-table-pagination";
import { DataTableToolbar } from "./data-table-toolbar";
import { RowActionMenu } from "./row-action-menu";
import { SavedViewTabs } from "./saved-view-tabs";
import type { DataTableColumn, DataTableFilter, DataTableSortDirection, RowAction, SavedViewTab } from "./types";
import { DetailDrawer } from "@/components/layout/detail-drawer";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/states";
import { cn } from "@/lib/utils";

function getCellValue<TData>(row: TData, column: DataTableColumn<TData>): string {
  const value = typeof column.accessor === "function" ? column.accessor(row) : column.accessor ? row[column.accessor] : "";
  return value === null || value === undefined ? "" : String(value);
}

function compareValues(a: string, b: string, direction: DataTableSortDirection): number {
  const result = a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
  return direction === "asc" ? result : -result;
}

export function DataTable<TData extends { id: string }>({
  data,
  columns,
  getRowSearchText,
  filters = [],
  savedViews = [{ id: "all", label: "All" }],
  activeView = "all",
  onViewChange,
  rowActions = [],
  pageSize = 8,
  isLoading = false,
  error,
  label = "Data table",
  getDrawerTitle,
  renderDrawer,
}: {
  data: TData[];
  columns: DataTableColumn<TData>[];
  getRowSearchText?: (row: TData) => string;
  filters?: DataTableFilter[];
  savedViews?: SavedViewTab[];
  activeView?: string;
  onViewChange?: (view: string) => void;
  rowActions?: RowAction<TData>[];
  pageSize?: number;
  isLoading?: boolean;
  error?: { title?: string; description?: string; requestId?: string | null } | null;
  label?: string;
  getDrawerTitle?: (row: TData) => string;
  renderDrawer?: (row: TData) => ReactNode;
}) {
  const [search, setSearch] = useState("");
  const [internalActiveView, setInternalActiveView] = useState(activeView);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sort, setSort] = useState<{ columnId: string; direction: DataTableSortDirection } | null>(null);
  const [page, setPage] = useState(0);
  const [drawerRow, setDrawerRow] = useState<TData | null>(null);

  const currentActiveView = onViewChange ? activeView : internalActiveView;

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    const rows = normalizedSearch
      ? data.filter((row) => {
          const rowText = getRowSearchText?.(row) ?? columns.map((column) => getCellValue(row, column)).join(" ");
          return rowText.toLowerCase().includes(normalizedSearch);
        })
      : data;

    if (!sort) return rows;
    const column = columns.find((item) => item.id === sort.columnId);
    if (!column) return rows;

    return [...rows].sort((a, b) => compareValues(getCellValue(a, column), getCellValue(b, column), sort.direction));
  }, [columns, data, getRowSearchText, search, sort]);

  const pageCount = Math.max(Math.ceil(filteredRows.length / pageSize), 1);
  const safePage = Math.min(page, pageCount - 1);
  const pagedRows = filteredRows.slice(safePage * pageSize, safePage * pageSize + pageSize);
  const visibleIds = pagedRows.map((row) => row.id);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selected.has(id));

  function toggleSort(column: DataTableColumn<TData>) {
    if (!column.sortable) return;
    setSort((current) => {
      if (current?.columnId !== column.id) return { columnId: column.id, direction: "asc" };
      if (current.direction === "asc") return { columnId: column.id, direction: "desc" };
      return null;
    });
  }

  function toggleRow(rowId: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(rowId)) next.delete(rowId);
      else next.add(rowId);
      return next;
    });
  }

  function toggleVisibleRows() {
    setSelected((current) => {
      const next = new Set(current);
      if (allVisibleSelected) visibleIds.forEach((id) => next.delete(id));
      else visibleIds.forEach((id) => next.add(id));
      return next;
    });
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-panel shadow-panel">
      <div className="space-y-3 p-4">
        <SavedViewTabs
          tabs={savedViews}
          activeTab={currentActiveView}
          onChange={(view) => {
            setInternalActiveView(view);
            onViewChange?.(view);
          }}
        />
        <BulkActionBar selectedCount={selected.size} onClear={() => setSelected(new Set())} />
      </div>
      <DataTableToolbar
        search={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(0);
        }}
        filters={filters}
      >
        <Button type="button" variant="secondary" size="sm" disabled aria-label="Save view disabled because backend saved-view API is pending" title="Backend saved-view API is pending">
          Save view
        </Button>
        <Button type="button" variant="locked" size="sm" disabled aria-label="Bulk actions disabled because backend mutation APIs are pending" title="Backend bulk mutation APIs are pending">
          Bulk API locked
        </Button>
      </DataTableToolbar>

      {isLoading ? <DataTableLoadingState /> : null}
      {error ? <ErrorState title={error.title ?? "Table failed"} description={error.description ?? "The table failed safely."} requestId={error.requestId} /> : null}

      {!isLoading && !error ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left text-small" aria-label={label}>
            <thead className="bg-panel2 text-caption uppercase tracking-wide text-subtle">
              <tr>
                <th className="w-12 px-4 py-3">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-border bg-panel2 accent-blue"
                    aria-label="Select visible rows"
                    checked={allVisibleSelected}
                    onChange={toggleVisibleRows}
                  />
                </th>
                {columns.map((column) => (
                  <th key={column.id} className={cn("px-4 py-3 font-semibold", column.className)}>
                    <DataTableColumnHeader
                      label={column.header}
                      sortable={column.sortable}
                      direction={sort?.columnId === column.id ? sort.direction : null}
                      onSort={() => toggleSort(column)}
                    />
                  </th>
                ))}
                <th className="w-20 px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pagedRows.map((row) => (
                <tr key={row.id} className="border-t border-border hover:bg-panel2/60">
                  <td className="px-4 py-3 align-middle">
                    <input
                      type="checkbox"
                      className="size-4 rounded border-border bg-panel2 accent-blue"
                      aria-label={`Select row ${row.id}`}
                      checked={selected.has(row.id)}
                      onChange={() => toggleRow(row.id)}
                    />
                  </td>
                  {columns.map((column) => (
                    <td key={column.id} className={cn("px-4 py-3 align-middle text-muted", column.className)}>
                      {column.cell ? column.cell(row) : getCellValue(row, column)}
                    </td>
                  ))}
                  <td className="px-4 py-3 align-middle">
                    <div className="flex items-center justify-end gap-2">
                      {renderDrawer ? (
                        <Button type="button" variant="ghost" size="sm" onClick={() => setDrawerRow(row)} aria-label={`View details for row ${row.id}`}>
                          View
                        </Button>
                      ) : null}
                      <RowActionMenu row={row} actions={rowActions} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {pagedRows.length === 0 ? (
            <div className="p-4">
              <DataTableEmptyState />
            </div>
          ) : null}
        </div>
      ) : null}

      <DataTablePagination page={safePage} pageCount={pageCount} pageSize={pageSize} totalRows={filteredRows.length} onPageChange={setPage} />

      <DetailDrawer
        open={Boolean(drawerRow)}
        onOpenChange={(open) => {
          if (!open) setDrawerRow(null);
        }}
        title={drawerRow && getDrawerTitle ? getDrawerTitle(drawerRow) : "Row details"}
        description="Read-only local/demo detail drawer. Backend detail APIs are not wired in this slice."
      >
        {drawerRow && renderDrawer ? renderDrawer(drawerRow) : null}
      </DetailDrawer>
    </div>
  );
}
