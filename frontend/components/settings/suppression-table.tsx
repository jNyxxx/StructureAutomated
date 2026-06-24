"use client";

import { Lock, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { suppressionRows, type SuppressionRow } from "./settings-sample-data";

const columns: DataTableColumn<SuppressionRow>[] = [
  { id: "contact", header: "Contact", accessor: "contact", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.contact}</span> },
  { id: "company", header: "Company", accessor: "company", sortable: true },
  { id: "reason", header: "Reason", accessor: "reason", sortable: true },
  { id: "source", header: "Source", accessor: "source", sortable: true },
  { id: "status", header: "Status", accessor: "status", sortable: true, cell: (row) => <GateReasonBadge state="blocked" label={row.status} /> },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "All suppressed", count: suppressionRows.length },
  { id: "unsubscribed", label: "Unsubscribed", count: 1 },
  { id: "manual", label: "Manual blocks", count: 1 },
  { id: "export", label: "Export API", count: 0, locked: true },
];

export function SuppressionTable() {
  return (
    <DataTable
      label="Suppression demo table"
      data={suppressionRows}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[{ key: "runtime", label: "Runtime", value: "local/demo" }]}
      rowActions={[
        { label: "Add suppression", pendingBackend: true },
        { label: "Remove suppression", pendingBackend: true },
        { label: "Export", pendingBackend: true },
        { label: "Persist unsubscribe", pendingBackend: true },
      ]}
      getRowSearchText={(row) => `${row.contact} ${row.company} ${row.reason} ${row.status}`}
      getDrawerTitle={(row) => row.contact}
      renderDrawer={(row) => (
        <div className="space-y-3 text-small text-muted">
          <div className="rounded-medium border border-red/25 bg-redbg p-3">
            <div className="flex items-center gap-2 font-semibold text-text"><ShieldAlert className="size-4 text-red" /> Suppression is no-send</div>
            <p className="mt-1">This local/demo row blocks approval and sending. Persistence requires backend APIs.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-medium border border-border bg-panel2 p-3"><p className="font-semibold text-text">Reason</p><p>{row.reason}</p></div>
            <div className="rounded-medium border border-border bg-panel2 p-3"><p className="font-semibold text-text">Source</p><p>{row.source}</p></div>
          </div>
          <Button disabled><Lock className="size-4" /> Suppression mutation locked</Button>
        </div>
      )}
    />
  );
}
