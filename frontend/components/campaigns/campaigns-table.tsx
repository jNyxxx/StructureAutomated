"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, Clock3, Lock, ShieldAlert } from "lucide-react";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { campaignRows, type CampaignRow } from "./campaign-sample-data";

function CampaignStatusBadge({ status }: { status: CampaignRow["status"] }) {
  const config = {
    draft: { label: "Draft", variant: "default" as const, icon: Clock3 },
    researching: { label: "Researching", variant: "default" as const, icon: Clock3 },
    review: { label: "Review", variant: "warning" as const, icon: AlertTriangle },
    blocked: { label: "Blocked", variant: "danger" as const, icon: ShieldAlert },
    mock_ready: { label: "Mock ready", variant: "success" as const, icon: CheckCircle2 },
  }[status];
  const Icon = config.icon;
  return (
    <Badge variant={config.variant} className="gap-1.5">
      <Icon className="size-3.5" />
      {config.label}
    </Badge>
  );
}

function SendGateBadge({ state }: { state: CampaignRow["sendGateStatus"] }) {
  if (state === "passed") return <GateReasonBadge state="passed" label="Passed" />;
  if (state === "warning") return <GateReasonBadge state="warning" label="Warning" />;
  if (state === "pending") return <GateReasonBadge state="pending" label="Pending" />;
  return <GateReasonBadge state="blocked" label="Locked" />;
}

const columns: DataTableColumn<CampaignRow>[] = [
  {
    id: "name",
    header: "Campaign name",
    accessor: "name",
    sortable: true,
    cell: (row) => (
      <Link href={`/campaigns/${row.id}`} className="font-semibold text-text hover:text-blue">
        {row.name}
      </Link>
    ),
  },
  { id: "segment", header: "Segment / market", accessor: "segment", sortable: true },
  { id: "status", header: "Status", accessor: "status", sortable: true, cell: (row) => <CampaignStatusBadge status={row.status} /> },
  { id: "selectedProspects", header: "Selected prospects", accessor: "selectedProspects", sortable: true },
  { id: "researchProgress", header: "Research", accessor: "researchProgress", sortable: true },
  { id: "draftProgress", header: "Drafts", accessor: "draftProgress", sortable: true },
  { id: "reviewStatus", header: "Review", accessor: "reviewStatus", sortable: true },
  { id: "sendGateStatus", header: "Send gate", accessor: "sendGateStatus", sortable: true, cell: (row) => <SendGateBadge state={row.sendGateStatus} /> },
  { id: "followUpStatus", header: "Follow-up", accessor: "followUpStatus", sortable: true },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "All campaigns", count: campaignRows.length },
  { id: "review", label: "Needs review", count: 1 },
  { id: "blocked", label: "Blocked", count: 1 },
  { id: "live", label: "Live send", count: 0, locked: true },
];

export function CampaignsTable() {
  return (
    <DataTable
      label="Campaigns demo table"
      data={campaignRows}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[
        { key: "runtime", label: "Runtime", value: "local/demo" },
        { key: "api", label: "API", value: "pending backend" },
      ]}
      rowActions={[
        { label: "Open details" },
        { label: "Start research", pendingBackend: true },
        { label: "Generate drafts", pendingBackend: true },
        { label: "Mock send", pendingBackend: true },
        { label: "Export", pendingBackend: true },
      ]}
      getRowSearchText={(row) => `${row.name} ${row.segment} ${row.status} ${row.researchProgress} ${row.draftProgress} ${row.reviewStatus} ${row.safeSummary}`}
      getDrawerTitle={(row) => row.name}
      renderDrawer={(row) => (
        <div className="space-y-4 text-small text-muted">
          <p>{row.safeSummary}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <p className="font-semibold text-text">Selected prospects</p>
              <p>{row.selectedProspects}</p>
            </div>
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <p className="font-semibold text-text">Send gate</p>
              <SendGateBadge state={row.sendGateStatus} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="secondary" size="sm">
              <Link href={`/campaigns/${row.id}`}>Open detail page</Link>
            </Button>
            <Button disabled size="sm">
              <Lock className="size-4" /> Mutations locked
            </Button>
          </div>
        </div>
      )}
    />
  );
}
