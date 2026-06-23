"use client";

import { AlertTriangle, CheckCircle2, CopyX, ShieldAlert } from "lucide-react";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { ProspectDetailDrawer } from "./prospect-detail-drawer";
import { prospectRows, type ProspectRow } from "./prospect-sample-data";

function SuppressionBadge({ status }: { status: ProspectRow["suppressionStatus"] }) {
  const config = {
    clear: { label: "Clear", variant: "success" as const, icon: CheckCircle2 },
    suppressed: { label: "Suppressed", variant: "danger" as const, icon: ShieldAlert },
    duplicate: { label: "Duplicate", variant: "locked" as const, icon: CopyX },
    needs_review: { label: "Needs review", variant: "warning" as const, icon: AlertTriangle },
  }[status];
  const Icon = config.icon;
  return (
    <Badge variant={config.variant} className="gap-1.5">
      <Icon className="size-3.5" />
      {config.label}
    </Badge>
  );
}

function ResearchBadge({ status }: { status: ProspectRow["researchStatus"] }) {
  if (status === "grounded") return <GateReasonBadge state="passed" label="Grounded" />;
  if (status === "blocked") return <GateReasonBadge state="blocked" label="Blocked" />;
  if (status === "queued") return <GateReasonBadge state="pending" label="Queued" />;
  return <GateReasonBadge state="missing" label="Not started" />;
}

function CampaignBadge({ status }: { status: ProspectRow["campaignStatus"] }) {
  const mapped = {
    not_assigned: "skipped",
    draft_ready: "draft_generated",
    pending_review: "pending_review",
    mock_queued: "mock_queued",
    blocked: "blocked",
  } as const;
  return <StatusBadge status={mapped[status]} />;
}

const columns: DataTableColumn<ProspectRow>[] = [
  { id: "name", header: "Name", accessor: "name", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.name}</span> },
  { id: "company", header: "Company", accessor: "company", sortable: true },
  { id: "title", header: "Role / title", accessor: "title", sortable: true },
  { id: "emailDomain", header: "Email / domain", accessor: "emailDomain", sortable: true },
  { id: "marketSegment", header: "Market / segment", accessor: "marketSegment", sortable: true },
  { id: "source", header: "Source", accessor: "source", sortable: true },
  { id: "suppressionStatus", header: "Suppression", accessor: "suppressionStatus", sortable: true, cell: (row) => <SuppressionBadge status={row.suppressionStatus} /> },
  { id: "researchStatus", header: "Research", accessor: "researchStatus", sortable: true, cell: (row) => <ResearchBadge status={row.researchStatus} /> },
  { id: "campaignStatus", header: "Campaign", accessor: "campaignStatus", sortable: true, cell: (row) => <CampaignBadge status={row.campaignStatus} /> },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "All prospects", count: prospectRows.length },
  { id: "ready", label: "Ready for review", count: 1 },
  { id: "blocked", label: "Suppressed/blocked", count: 1 },
  { id: "campaign", label: "Campaign API", count: 0, locked: true },
];

export function ProspectsTable() {
  return (
    <DataTable
      label="Prospects demo table"
      data={prospectRows}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[
        { key: "runtime", label: "Runtime", value: "local/demo" },
        { key: "api", label: "API", value: "pending backend" },
      ]}
      rowActions={[
        { label: "Open details" },
        { label: "Enrich prospect", pendingBackend: true },
        { label: "Add to campaign", pendingBackend: true },
        { label: "Delete prospect", pendingBackend: true, disabled: true },
      ]}
      getRowSearchText={(row) => `${row.name} ${row.company} ${row.title} ${row.emailDomain} ${row.marketSegment} ${row.source} ${row.safeNotes}`}
      getDrawerTitle={(row) => row.name}
      renderDrawer={(row) => <ProspectDetailDrawer prospect={row} />}
    />
  );
}
