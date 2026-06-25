"use client";

import { useCallback, useEffect, useState } from "react";
import { Lock, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { fetchSuppressions } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import type { Suppression } from "@/lib/schemas";
import { suppressionRows, type SuppressionRow } from "./settings-sample-data";

const columns: DataTableColumn<SuppressionRow>[] = [
  { id: "contact", header: "Contact", accessor: "contact", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.contact}</span> },
  { id: "company", header: "Company", accessor: "company", sortable: true },
  { id: "reason", header: "Reason", accessor: "reason", sortable: true },
  { id: "source", header: "Source", accessor: "source", sortable: true },
  { id: "status", header: "Status", accessor: "status", sortable: true, cell: (row) => <GateReasonBadge state="blocked" label={row.status} /> },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

function mapSuppression(suppression: Suppression, index: number): SuppressionRow {
  return {
    id: suppression.id,
    contact: `Suppressed contact ${index + 1}`,
    company: "Identifier redacted",
    reason: suppression.reason,
    source: suppression.source,
    status: suppression.active ? "suppressed" : "manual_block",
    updatedAt: new Date(suppression.created_at).toLocaleDateString(),
  };
}

export function SuppressionTable() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [rows, setRows] = useState<SuppressionRow[]>(suppressionRows);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  const loadSuppressions = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setRows(suppressionRows);
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await fetchSuppressions(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        { limit: 25 },
      );
      const mapped = res.suppressions.map(mapSuppression);
      setRows(mapped.length > 0 ? mapped : suppressionRows);
      setUsingFallback(mapped.length === 0);
    } catch (err) {
      console.error("Failed to load suppressions, falling back to read-only local/mock data:", err);
      setRows(suppressionRows);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadSuppressions();
  }, [loadSuppressions]);

  const views: SavedViewTab[] = [
    { id: "all", label: "All suppressed", count: rows.length },
    { id: "unsubscribed", label: "Unsubscribed", count: rows.filter((row) => row.status === "unsubscribed").length },
    { id: "manual", label: "Manual blocks", count: rows.filter((row) => row.status === "manual_block").length },
    { id: "export", label: "Export API", count: 0, locked: true },
  ];

  return (
    <DataTable
      label="Suppression demo table"
      data={rows}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[{ key: "runtime", label: "Runtime", value: loading ? "loading..." : usingFallback ? "fixture fallback" : "backend mock API" }]}
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
            <p className="mt-1">This read-only local/mock row blocks approval and sending. Mutations, webhooks, and provider sync remain deferred.</p>
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
