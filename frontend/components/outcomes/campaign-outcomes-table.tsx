"use client";

import { GateReasonBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { campaignOutcomeRows, type CampaignOutcomeRow } from "./outcomes-sample-data";

function RoiStatusBadge({ status }: { status: CampaignOutcomeRow["roiStatus"] }) {
  if (status === "preview") return <GateReasonBadge state="warning" label="Preview" />;
  if (status === "pending") return <GateReasonBadge state="pending" label="Pending" />;
  return <GateReasonBadge state="blocked" label="Blocked" />;
}

const columns: DataTableColumn<CampaignOutcomeRow>[] = [
  { id: "campaign", header: "Campaign", accessor: "campaign", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.campaign}</span> },
  { id: "segment", header: "Segment", accessor: "segment", sortable: true },
  { id: "mockSent", header: "Mock sent", accessor: "mockSent", sortable: true },
  { id: "replies", header: "Replies", accessor: "replies", sortable: true },
  { id: "meetings", header: "Meetings", accessor: "meetings", sortable: true },
  { id: "opportunities", header: "Opportunities", accessor: "opportunities", sortable: true },
  { id: "pipelineValue", header: "Pipeline", accessor: "pipelineValue", sortable: true },
  { id: "roiStatus", header: "ROI status", accessor: "roiStatus", sortable: true, cell: (row) => <RoiStatusBadge status={row.roiStatus} /> },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "All outcomes", count: campaignOutcomeRows.length },
  { id: "preview", label: "Preview ROI", count: 1 },
  { id: "blocked", label: "Blocked", count: 1 },
  { id: "crm", label: "CRM sync", count: 0, locked: true },
];

export function CampaignOutcomesTable() {
  return (
    <DataTable
      label="Campaign outcomes demo table"
      data={campaignOutcomeRows}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[
        { key: "runtime", label: "Runtime", value: "local/demo" },
        { key: "api", label: "API", value: "pending backend" },
      ]}
      rowActions={[
        { label: "Open outcome details" },
        { label: "Export outcomes", pendingBackend: true },
        { label: "Sync CRM", pendingBackend: true },
        { label: "Recalculate ROI", pendingBackend: true },
      ]}
      getRowSearchText={(row) => `${row.campaign} ${row.segment} ${row.pipelineValue} ${row.roiStatus}`}
      getDrawerTitle={(row) => row.campaign}
      renderDrawer={(row) => (
        <div className="space-y-3 text-small text-muted">
          <p>Read-only local/demo outcome row. No CRM, payment, revenue, or attribution API is wired.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <p className="font-semibold text-text">Pipeline assumption</p>
              <p>{row.pipelineValue}</p>
            </div>
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <p className="font-semibold text-text">ROI status</p>
              <RoiStatusBadge status={row.roiStatus} />
            </div>
          </div>
        </div>
      )}
    />
  );
}
