"use client";

import Link from "next/link";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { draftRows, type DraftRow } from "./draft-sample-data";
import { DraftDetailDrawer } from "./draft-detail-drawer";

function GateBadge({ state, label }: { state: DraftRow["promptInjectionGate"]; label?: string }) {
  return <GateReasonBadge state={state} label={label} />;
}

const columns: DataTableColumn<DraftRow>[] = [
  { id: "subject", header: "Draft subject", accessor: "subject", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.subject}</span> },
  { id: "prospectCompany", header: "Prospect / company", accessor: "prospectCompany", sortable: true },
  { id: "campaign", header: "Campaign", accessor: "campaign", sortable: true, cell: (row) => <Link href={`/campaigns/${row.campaignId}`} className="text-blue hover:text-cyan">{row.campaign}</Link> },
  { id: "status", header: "Draft status", accessor: "status", sortable: true, cell: (row) => <StatusBadge status={row.status} /> },
  { id: "promptInjectionGate", header: "Prompt injection", accessor: "promptInjectionGate", sortable: true, cell: (row) => <GateBadge state={row.promptInjectionGate} /> },
  { id: "sourceTrustGate", header: "Source trust", accessor: "sourceTrustGate", sortable: true, cell: (row) => <GateBadge state={row.sourceTrustGate} /> },
  { id: "groundednessGate", header: "Groundedness", accessor: "groundednessGate", sortable: true, cell: (row) => <GateBadge state={row.groundednessGate} /> },
  { id: "reviewStatus", header: "Review", accessor: "reviewStatus", sortable: true, cell: (row) => <StatusBadge status={row.reviewStatus} /> },
  { id: "sendGateReadiness", header: "Send gate", accessor: "sendGateReadiness", sortable: true, cell: (row) => <GateBadge state={row.sendGateReadiness} label="Locked" /> },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "All drafts", count: draftRows.length },
  { id: "needs_regeneration", label: "Needs regeneration", count: 1 },
  { id: "blocked", label: "Blocked", count: 1 },
  { id: "send_ready", label: "Send ready", count: 0, locked: true },
];

export function DraftsTable({ rows = draftRows }: { rows?: DraftRow[] }) {
  return (
    <DataTable
      label="AI drafts demo table"
      data={rows}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[
        { key: "runtime", label: "Runtime", value: "local/demo" },
        { key: "api", label: "API", value: "pending backend" },
      ]}
      rowActions={[
        { label: "Open preview" },
        { label: "Generate draft", pendingBackend: true },
        { label: "Regenerate", pendingBackend: true },
        { label: "Approve", pendingBackend: true },
        { label: "Send", pendingBackend: true },
      ]}
      getRowSearchText={(row) => `${row.subject} ${row.prospectCompany} ${row.campaign} ${row.status} ${row.reviewStatus} ${row.body}`}
      getDrawerTitle={(row) => row.subject}
      renderDrawer={(row) => <DraftDetailDrawer draft={row} />}
    />
  );
}
