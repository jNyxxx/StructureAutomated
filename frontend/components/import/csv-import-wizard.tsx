"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Database, Loader2, Upload } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { importContacts } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { CsvUploadDropzone } from "./csv-upload-dropzone";
import { ColumnMapper } from "./column-mapper";
import { ImportValidationSummary } from "./import-validation-summary";
import { ImportRowsTable } from "./import-rows-table";
import { importPreviewRows, sampleCsvColumns } from "./sample-import-data";

const steps = ["Upload CSV", "Column mapping", "Validation summary", "Preview rows", "Backend mock import"];

type ImportState = "idle" | "submitting" | "success" | "error";

function buildMockCsvText(): string {
  const rows = importPreviewRows.map((row) => [row.fullName, row.company, row.title, row.domain, row.segment].join(","));
  return [sampleCsvColumns.join(","), ...rows].join("\n");
}

export function CsvImportWizard() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [state, setState] = useState<ImportState>("idle");
  const [summary, setSummary] = useState<{
    id: string;
    status: string;
    totalRows: number;
    validRows: number;
    invalidRows: number;
    duplicateRows: number;
    replay: boolean;
  } | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);

  const csvText = useMemo(buildMockCsvText, []);
  const canSubmit = auth.isLoaded && auth.isSignedIn && Boolean(selectedTenantId) && state !== "submitting";

  async function handleSubmit() {
    if (!canSubmit || !selectedTenantId) return;

    setState("submitting");
    setSummary(null);
    setError(null);

    try {
      const res = await importContacts(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        {
          csv_text: csvText,
          source_filename: "prospects_demo.csv",
        },
      );
      const importSummary = res.import;
      if (!importSummary) {
        setError({
          message: "The backend mock API did not return an import summary. No success was recorded.",
          code: "IMPORT_SUMMARY_MISSING",
          requestId: null,
        });
        setState("error");
        return;
      }
      setSummary({
        id: importSummary.id,
        status: importSummary.status,
        totalRows: importSummary.total_rows,
        validRows: importSummary.valid_rows,
        invalidRows: importSummary.invalid_rows,
        duplicateRows: importSummary.duplicate_rows,
        replay: res.idempotency_replay,
      });
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock import failed safely. No contacts were imported.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-panel p-4 shadow-panel">
        <div className="grid gap-3 md:grid-cols-5">
          {steps.map((step, index) => (
            <div key={step} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-caption text-subtle">
                {index < 4 ? <CheckCircle2 className="size-4 text-blue" /> : <Database className="size-4 text-green" />}
                Step {index + 1}
              </div>
              <p className="mt-1 text-small font-semibold text-text">{step}</p>
            </div>
          ))}
        </div>
      </div>

      <CsvUploadDropzone />
      <ColumnMapper />
      <ImportValidationSummary />
      <ImportRowsTable />

      <div className="rounded-xl border border-blue/30 bg-bluebg/40 p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Upload className="size-4 text-blue" /> Local/mock import confirmation
            </div>
            <p className="mt-2 text-small text-muted">
              This submits the sample CSV to the backend mock API only. No live scraping, enrichment, campaign assignment, real sending, provider call, or production import is enabled.
            </p>
          </div>
          <GateReasonBadge state="passed" label="Backend mock import" />
        </div>

        {state === "success" && summary ? (
          <div className="mt-4 rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> Backend mock import succeeded
            </div>
            <div className="mt-3 grid gap-3 text-small text-muted md:grid-cols-4">
              <span>Total rows: <strong className="text-text">{summary.totalRows}</strong></span>
              <span>Valid rows: <strong className="text-text">{summary.validRows}</strong></span>
              <span>Invalid rows: <strong className="text-text">{summary.invalidRows}</strong></span>
              <span>Duplicates: <strong className="text-text">{summary.duplicateRows}</strong></span>
            </div>
            <p className="mt-3 text-caption text-muted">
              Status: {summary.status}. Import ID: {summary.id}. {summary.replay ? "Idempotency replay was returned." : "New backend mock import response was returned."}
            </p>
            <Button asChild className="mt-4" variant="secondary">
              <Link href="/prospects">View prospects from backend mock API</Link>
            </Button>
          </div>
        ) : null}

        {state === "error" && error ? (
          <div className="mt-4 rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> Backend mock import failed safely
            </div>
            <p className="mt-2 text-small text-muted">{error.message}</p>
            <p className="mt-2 text-caption text-muted">
              Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No fake success was recorded.
            </p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {state === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
            {state === "submitting" ? "Importing via backend mock API" : "Import prospects"}
          </Button>
          <Button variant="secondary" disabled>
            Save mapping
          </Button>
        </div>
      </div>
    </div>
  );
}
