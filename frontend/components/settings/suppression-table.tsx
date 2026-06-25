"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, Lock, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { createSuppression, fetchSuppressions, reinstateSuppression } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { isStrictBackendMode } from "@/lib/runtime-mode";
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

type ActionState = "idle" | "submitting" | "success" | "error";
type SuppressionAction = "create" | "reinstate";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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
  const strictBackendMode = isStrictBackendMode();
  const [rows, setRows] = useState<SuppressionRow[]>(suppressionRows);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [strictError, setStrictError] = useState<string | null>(null);
  const [state, setState] = useState<ActionState>("idle");
  const [activeAction, setActiveAction] = useState<SuppressionAction | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);

  const loadSuppressions = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      if (strictBackendMode) {
        setStrictError("Suppressions backend mock API read did not complete in strict backend mode.");
        setLoading(false);
        return;
      }
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
      setStrictError(null);
    } catch (err) {
      if (strictBackendMode) {
        setStrictError("Suppressions backend mock API read failed in strict backend mode.");
      } else {
        console.error("Failed to load suppressions, falling back to local/mock data:", err);
        setRows(suppressionRows);
        setUsingFallback(true);
      }
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, strictBackendMode]);

  useEffect(() => {
    loadSuppressions();
  }, [loadSuppressions]);

  async function handleCreateSuppression() {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || state === "submitting") return;

    setState("submitting");
    setActiveAction("create");
    setMessage(null);
    setError(null);

    try {
      const res = await createSuppression(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        {
          channel: "email",
          contact_identifier: "local-mock-suppression@example.com",
          reason: "Local/mock manual suppression from settings UI",
          source: "backend_mock_api",
          never_contact: true,
        },
      );
      setMessage(`Backend mock suppression created: ${res.suppression.id}. Relevant read surface refresh was requested.`);
      setRows((current) => [mapSuppression(res.suppression, 0), ...current.filter((row) => row.id !== res.suppression.id)]);
      setUsingFallback(false);
      setState("success");
      await loadSuppressions();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock suppression create failed safely. No provider sync or webhook was triggered.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  async function handleReinstateSuppression() {
    const target = rows.find((row) => UUID_RE.test(row.id));
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || !target || state === "submitting") return;

    setState("submitting");
    setActiveAction("reinstate");
    setMessage(null);
    setError(null);

    try {
      const res = await reinstateSuppression(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        target.id,
      );
      setMessage(`Backend mock suppression reinstated: ${res.suppression.id}. Relevant read surface refresh was requested.`);
      setRows((current) => [mapSuppression(res.suppression, 0), ...current.filter((row) => row.id !== res.suppression.id)]);
      setUsingFallback(false);
      setState("success");
      await loadSuppressions();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock suppression reinstate failed safely. No provider sync or webhook was triggered.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  if (strictError) {
    return <ErrorState title="Strict backend mode: suppressions failed" description={strictError} />;
  }

  const views: SavedViewTab[] = [
    { id: "all", label: "All suppressed", count: rows.length },
    { id: "unsubscribed", label: "Unsubscribed", count: rows.filter((row) => row.status === "unsubscribed").length },
    { id: "manual", label: "Manual blocks", count: rows.filter((row) => row.status === "manual_block").length },
    { id: "export", label: "Export API", count: 0, locked: true },
  ];

  const canReinstate = rows.some((row) => UUID_RE.test(row.id));

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-blue/30 bg-bluebg/40 p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-semibold text-text">Local/mock suppression actions</p>
            <p className="mt-2 text-small text-muted">
              Create and reinstate call the backend mock API only. No real unsubscribe webhook, bounce/complaint webhook, provider sync, real sending, export, or production action is triggered.
            </p>
          </div>
          <GateReasonBadge state="passed" label="Suppression mock actions" />
        </div>

        {message ? (
          <div className="mt-4 rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> {message}
            </div>
            <p className="mt-2 text-caption text-muted">No provider sync, webhook, export, privacy delete, or production compliance automation was triggered.</p>
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> Backend mock suppression action failed safely
            </div>
            <p className="mt-2 text-small text-muted">{error.message}</p>
            <p className="mt-2 text-caption text-muted">
              Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No fake success was recorded.
            </p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={handleCreateSuppression} disabled={!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || state === "submitting"}>
            {state === "submitting" && activeAction === "create" ? <Loader2 className="size-4 animate-spin" /> : <ShieldAlert className="size-4" />}
            {state === "submitting" && activeAction === "create" ? "Creating via backend mock API" : "Create local/mock suppression"}
          </Button>
          <Button onClick={handleReinstateSuppression} disabled={!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || !canReinstate || state === "submitting"} variant="secondary">
            {state === "submitting" && activeAction === "reinstate" ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
            {state === "submitting" && activeAction === "reinstate" ? "Reinstating via backend mock API" : "Reinstate local/mock suppression"}
          </Button>
          <Button disabled variant="locked">
            <Lock className="size-4" /> Provider sync locked
          </Button>
          <Button disabled variant="locked">
            Export locked
          </Button>
        </div>
      </div>

      <DataTable
        label="Suppression demo table"
        data={rows}
        columns={columns}
        savedViews={views}
        pageSize={6}
        filters={[{ key: "runtime", label: "Runtime", value: loading ? "loading..." : usingFallback ? "fixture fallback" : "backend mock API" }]}
        rowActions={[
          { label: "Create in action panel" },
          { label: "Reinstate in action panel" },
          { label: "Provider sync", pendingBackend: true, disabled: true },
          { label: "Export", pendingBackend: true, disabled: true },
        ]}
        getRowSearchText={(row) => `${row.contact} ${row.company} ${row.reason} ${row.status}`}
        getDrawerTitle={(row) => row.contact}
        renderDrawer={(row) => (
          <div className="space-y-3 text-small text-muted">
            <div className="rounded-medium border border-red/25 bg-redbg p-3">
              <div className="flex items-center gap-2 font-semibold text-text"><ShieldAlert className="size-4 text-red" /> Suppression is no-send</div>
              <p className="mt-1">This local/mock row blocks approval and sending. Real webhooks, provider sync, and production compliance automation remain deferred.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-medium border border-border bg-panel2 p-3"><p className="font-semibold text-text">Reason</p><p>{row.reason}</p></div>
              <div className="rounded-medium border border-border bg-panel2 p-3"><p className="font-semibold text-text">Source</p><p>{row.source}</p></div>
            </div>
            <Button disabled><Lock className="size-4" /> Provider sync locked</Button>
          </div>
        )}
      />
    </div>
  );
}
