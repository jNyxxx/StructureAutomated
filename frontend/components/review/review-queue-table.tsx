"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { fetchReviewItems } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { ReviewWorkspace } from "./review-workspace";
import { reviewDtoToItem, reviewItems, type ReviewItem } from "./review-sample-data";

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

export function ReviewQueueTable() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [rows, setRows] = useState<ReviewItem[]>(reviewItems);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  const loadReviewItems = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setRows(reviewItems);
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await fetchReviewItems(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        { limit: 25 },
      );
      const mapped = res.review_items.map((item) => reviewDtoToItem(item, reviewItems.find((row) => row.id === item.id)));
      setRows(mapped.length > 0 ? mapped : reviewItems);
      setUsingFallback(mapped.length === 0);
    } catch (err) {
      console.error("Failed to load review queue, falling back to read-only local/mock review data:", err);
      setRows(reviewItems);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadReviewItems();
  }, [loadReviewItems]);

  const views: SavedViewTab[] = [
    { id: "all", label: "All review items", count: rows.length },
    { id: "pending", label: "Pending review", count: rows.filter((row) => row.reviewStatus === "pending_review").length },
    { id: "regeneration", label: "Needs regeneration", count: rows.filter((row) => row.reviewStatus === "needs_regeneration").length },
    { id: "blocked", label: "Blocked", count: rows.filter((row) => row.reviewStatus === "blocked").length },
    { id: "bulk", label: "Bulk approval", count: 0, locked: true },
  ];

  return (
    <DataTable
      label="Review queue demo table"
      data={rows}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[
        { key: "runtime", label: "Runtime", value: loading ? "loading..." : usingFallback ? "fixture fallback" : "backend mock API" },
        { key: "api", label: "API", value: "review mock actions" },
      ]}
      rowActions={[
        { label: "Open review workspace" },
        { label: "Approve in workspace" },
        { label: "Reject in workspace" },
        { label: "Request regeneration in workspace" },
        { label: "Mock send", pendingBackend: true, disabled: true },
        { label: "Export", pendingBackend: true, disabled: true },
      ]}
      getRowSearchText={(row) => `${row.prospectCompany} ${row.campaign} ${row.draftSubject} ${row.reviewStatus} ${row.assignedReviewer}`}
      getDrawerTitle={(row) => row.draftSubject}
      renderDrawer={(row) => <ReviewWorkspace item={row} onListRefresh={loadReviewItems} />}
    />
  );
}
