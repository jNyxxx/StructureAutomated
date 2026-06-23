"use client";

import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { ReviewWorkspace } from "./review-workspace";
import { reviewItems, type ReviewItem } from "./review-sample-data";

function SuppressionBadge({ status }: { status: ReviewItem["suppressionStatus"] }) {
  const config = {
    clear: { label: "Clear", variant: "success" as const, icon: CheckCircle2 },
    suppressed: { label: "Suppressed", variant: "danger" as const, icon: ShieldAlert },
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

const columns: DataTableColumn<ReviewItem>[] = [
  { id: "prospectCompany", header: "Prospect / company", accessor: "prospectCompany", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.prospectCompany}</span> },
  { id: "campaign", header: "Campaign", accessor: "campaign", sortable: true },
  { id: "draftSubject", header: "Draft subject", accessor: "draftSubject", sortable: true },
  { id: "reviewStatus", header: "Review status", accessor: "reviewStatus", sortable: true, cell: (row) => <StatusBadge status={row.reviewStatus} /> },
  { id: "promptInjectionGate", header: "Prompt injection", accessor: (row) => row.draft.promptInjectionGate, sortable: true, cell: (row) => <GateReasonBadge state={row.draft.promptInjectionGate} /> },
  { id: "sourceTrustGate", header: "Source trust", accessor: (row) => row.draft.sourceTrustGate, sortable: true, cell: (row) => <GateReasonBadge state={row.draft.sourceTrustGate} /> },
  { id: "groundednessGate", header: "Groundedness", accessor: (row) => row.draft.groundednessGate, sortable: true, cell: (row) => <GateReasonBadge state={row.draft.groundednessGate} /> },
  { id: "suppressionStatus", header: "Suppression", accessor: "suppressionStatus", sortable: true, cell: (row) => <SuppressionBadge status={row.suppressionStatus} /> },
  { id: "sendReadiness", header: "Send readiness", accessor: "sendReadiness", sortable: true, cell: (row) => <GateReasonBadge state={row.sendReadiness} label="Locked" /> },
  { id: "assignedReviewer", header: "Reviewer", accessor: "assignedReviewer", sortable: true },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "All review items", count: reviewItems.length },
  { id: "pending", label: "Pending review", count: 1 },
  { id: "regeneration", label: "Needs regeneration", count: 1 },
  { id: "blocked", label: "Blocked", count: 1 },
  { id: "bulk", label: "Bulk approval", count: 0, locked: true },
];

export function ReviewQueueTable() {
  return (
    <DataTable
      label="Review queue demo table"
      data={reviewItems}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[
        { key: "runtime", label: "Runtime", value: "local/demo" },
        { key: "api", label: "API", value: "pending backend" },
      ]}
      rowActions={[
        { label: "Open review workspace" },
        { label: "Approve", pendingBackend: true },
        { label: "Reject", pendingBackend: true },
        { label: "Request regeneration", pendingBackend: true },
        { label: "Mock send", pendingBackend: true },
        { label: "Export", pendingBackend: true },
      ]}
      getRowSearchText={(row) => `${row.prospectCompany} ${row.campaign} ${row.draftSubject} ${row.reviewStatus} ${row.assignedReviewer}`}
      getDrawerTitle={(row) => row.draftSubject}
      renderDrawer={(row) => <ReviewWorkspace item={row} />}
    />
  );
}
