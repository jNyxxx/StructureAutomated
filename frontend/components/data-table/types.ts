import type { ReactNode } from "react";

export type DataTableSortDirection = "asc" | "desc";

export interface DataTableSortState<TData> {
  key: keyof TData | string;
  direction: DataTableSortDirection;
}

export interface DataTableColumn<TData> {
  id: string;
  header: string;
  accessor?: keyof TData | ((row: TData) => string | number | boolean | null | undefined);
  cell?: (row: TData) => ReactNode;
  sortable?: boolean;
  className?: string;
}

export interface DataTableFilter {
  key: string;
  label: string;
  value: string;
}

export interface SavedViewTab {
  id: string;
  label: string;
  count?: number;
  locked?: boolean;
}

export interface RowAction<TData> {
  label: string;
  onSelect?: (row: TData) => void;
  disabled?: boolean;
  pendingBackend?: boolean;
}
