"use client";

import { Badge } from "@/components/ui/badge";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { importPreviewRows, type ImportPreviewRow } from "./sample-import-data";

function ValidationBadge({ validation }: { validation: ImportPreviewRow["validation"] }) {
  const config = {
    valid: { label: "Valid", variant: "success" as const },
    warning: { label: "Needs review", variant: "warning" as const },
    blocked: { label: "Blocked", variant: "danger" as const },
  }[validation];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

const columns: DataTableColumn<ImportPreviewRow>[] = [
  { id: "fullName", header: "Name", accessor: "fullName", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.fullName}</span> },
  { id: "company", header: "Company", accessor: "company", sortable: true },
  { id: "title", header: "Role / title", accessor: "title", sortable: true },
  { id: "domain", header: "Domain", accessor: "domain", sortable: true },
  { id: "segment", header: "Segment", accessor: "segment", sortable: true },
  { id: "validation", header: "Validation", accessor: "validation", sortable: true, cell: (row) => <ValidationBadge validation={row.validation} /> },
  { id: "note", header: "Note", accessor: "note", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "Preview rows", count: importPreviewRows.length },
  { id: "blocked", label: "Blocked", count: 1 },
  { id: "import", label: "Backend mock import", count: importPreviewRows.length },
];

export function ImportRowsTable() {
  return (
    <DataTable
      label="CSV import preview rows"
      data={importPreviewRows}
      columns={columns}
      savedViews={views}
      pageSize={5}
      filters={[{ key: "source", label: "Source", value: "sample CSV" }]}
      rowActions={[
        { label: "Accept row", pendingBackend: true },
        { label: "Suppress row", pendingBackend: true },
        { label: "Delete row", pendingBackend: true, disabled: true },
      ]}
      getRowSearchText={(row) => `${row.fullName} ${row.company} ${row.title} ${row.domain} ${row.segment} ${row.note}`}
      getDrawerTitle={(row) => row.fullName}
      renderDrawer={(row) => (
        <div className="space-y-3 text-small text-muted">
          <p>Read-only sample CSV preview. Final confirmation can submit these rows to the backend mock import API only.</p>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="font-semibold text-text">Validation note</p>
            <p>{row.note}</p>
          </div>
        </div>
      )}
    />
  );
}
