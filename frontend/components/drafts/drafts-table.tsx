"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle2, Loader2, Lock, Sparkles } from "lucide-react";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { fetchDraft, fetchDraftEvidence, generateDraft } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { draftRows, draftToRow, evidenceToItem, type DraftRow } from "./draft-sample-data";
import { DraftDetailDrawer } from "./draft-detail-drawer";

const mockDraftRequest = {
  campaign_id: "44444444-4444-4444-4444-444444444444",
  contact_id: "22222222-2222-2222-2222-222222222222",
};

type ActionState = "idle" | "submitting" | "success" | "error";

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

function buildViews(rows: DraftRow[]): SavedViewTab[] {
  return [
    { id: "all", label: "All drafts", count: rows.length },
    { id: "needs_regeneration", label: "Needs regeneration", count: rows.filter((row) => row.status === "needs_regeneration").length },
    { id: "blocked", label: "Blocked", count: rows.filter((row) => row.status === "blocked").length },
    { id: "send_ready", label: "Send ready", count: 0, locked: true },
  ];
}

export function DraftsTable({ rows = draftRows }: { rows?: DraftRow[] }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [tableRows, setTableRows] = useState<DraftRow[]>(rows);
  const [state, setState] = useState<ActionState>("idle");
  const [generatedDraft, setGeneratedDraft] = useState<DraftRow | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);
  const canGenerate = auth.isLoaded && auth.isSignedIn && Boolean(selectedTenantId) && state !== "submitting";

  async function handleGenerateDraft() {
    if (!canGenerate || !selectedTenantId) return;

    setState("submitting");
    setGeneratedDraft(null);
    setMessage(null);
    setError(null);

    try {
      const res = await generateDraft(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        mockDraftRequest,
      );
      if (!res.draft) {
        setError({ message: "The backend mock API did not return a generated draft. No success was recorded.", code: "DRAFT_GENERATION_MISSING", requestId: null });
        setState("error");
        return;
      }

      const [draftRes, evidenceRes] = await Promise.all([
        fetchDraft(
          {
            getToken: auth.getToken,
            getTenantId: () => selectedTenantId,
          },
          res.draft.id,
        ),
        fetchDraftEvidence(
          {
            getToken: auth.getToken,
            getTenantId: () => selectedTenantId,
          },
          res.draft.id,
          { limit: 25 },
        ),
      ]);

      const generated = draftToRow(draftRes.draft, undefined, evidenceRes.evidence.map(evidenceToItem));
      setGeneratedDraft(generated);
      setTableRows((current) => [generated, ...current.filter((row) => row.id !== generated.id)]);
      setMessage(`Backend mock draft generation succeeded for ${generated.subject}. Detail and evidence were reloaded from backend mock read APIs.`);
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock draft generation failed safely. No draft was generated.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-blue/30 bg-bluebg/40 p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-semibold text-text">Local/mock draft generation</p>
            <p className="mt-2 text-small text-muted">
              This calls the backend mock API only. It does not call live AI providers, scrape websites, enrich contacts, approve reviews, run send gates, dispatch outbound messages, or enable production.
            </p>
          </div>
          <GateReasonBadge state="passed" label="Draft generation mock" />
        </div>

        {state === "success" && message ? (
          <div className="mt-4 rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> {message}
            </div>
            <p className="mt-2 text-caption text-muted">Generated draft detail/evidence reload uses GET /api/v1/drafts/{"{draft_id}"} and GET /api/v1/drafts/{"{draft_id}"}/evidence when available.</p>
          </div>
        ) : null}

        {state === "error" && error ? (
          <div className="mt-4 rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> Backend mock draft generation failed safely
            </div>
            <p className="mt-2 text-small text-muted">{error.message}</p>
            <p className="mt-2 text-caption text-muted">
              Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No fake success was recorded.
            </p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={handleGenerateDraft} disabled={!canGenerate}>
            {state === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            {state === "submitting" ? "Generating via backend mock API" : "Generate mock draft"}
          </Button>
          <Button disabled variant="secondary">
            <Lock className="size-4" /> Regenerate locked
          </Button>
          <Button disabled variant="secondary">
            <Lock className="size-4" /> Approve locked
          </Button>
          <Button disabled variant="secondary">
            <Lock className="size-4" /> Send locked
          </Button>
        </div>
      </div>

      {generatedDraft ? (
        <div className="rounded-xl border border-border bg-panel p-4 shadow-panel">
          <p className="mb-3 text-small font-semibold text-text">Generated draft detail/evidence preview</p>
          <DraftDetailDrawer draft={generatedDraft} />
        </div>
      ) : null}

      <DataTable
        label="AI drafts demo table"
        data={tableRows}
        columns={columns}
        savedViews={buildViews(tableRows)}
        pageSize={6}
        filters={[
          { key: "runtime", label: "Runtime", value: "local/mock data with backend mock generation" },
          { key: "api", label: "API", value: "draft generation + detail/evidence reads" },
        ]}
        rowActions={[
          { label: "Open preview" },
          { label: "Regenerate", pendingBackend: true, disabled: true },
          { label: "Approve", pendingBackend: true, disabled: true },
          { label: "Send", pendingBackend: true, disabled: true },
        ]}
        getRowSearchText={(row) => `${row.subject} ${row.prospectCompany} ${row.campaign} ${row.status} ${row.reviewStatus} ${row.body}`}
        getDrawerTitle={(row) => row.subject}
        renderDrawer={(row) => <DraftDetailDrawer draft={row} />}
      />
    </div>
  );
}
