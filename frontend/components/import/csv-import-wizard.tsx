import { CheckCircle2, Lock, Upload } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { CsvUploadDropzone } from "./csv-upload-dropzone";
import { ColumnMapper } from "./column-mapper";
import { ImportValidationSummary } from "./import-validation-summary";
import { ImportRowsTable } from "./import-rows-table";

const steps = ["Upload CSV", "Column mapping", "Validation summary", "Preview rows", "Locked confirmation"];

export function CsvImportWizard() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-panel p-4 shadow-panel">
        <div className="grid gap-3 md:grid-cols-5">
          {steps.map((step, index) => (
            <div key={step} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-caption text-subtle">
                {index < 4 ? <CheckCircle2 className="size-4 text-blue" /> : <Lock className="size-4 text-yellow" />}
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

      <div className="rounded-xl border border-yellow/30 bg-warnbg p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Upload className="size-4 text-yellow" /> Import confirmation locked
            </div>
            <p className="mt-2 text-small text-muted">
              Final import is disabled until a backend CSV import route exists. This UI does not upload, persist, enrich, scrape, or send anything.
            </p>
          </div>
          <GateReasonBadge state="blocked" label="Pending backend API" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button disabled>
            <Lock className="size-4" /> Import prospects
          </Button>
          <Button variant="secondary" disabled>
            Save mapping
          </Button>
        </div>
      </div>
    </div>
  );
}
