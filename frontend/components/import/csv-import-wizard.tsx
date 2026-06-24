import { CheckCircle2, Upload } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { CsvUploadDropzone } from "./csv-upload-dropzone";
import { ColumnMapper } from "./column-mapper";
import { ImportValidationSummary } from "./import-validation-summary";
import { ImportRowsTable } from "./import-rows-table";

const steps = ["Upload CSV", "Column mapping", "Validation summary", "Preview rows", "Confirmation"];

export function CsvImportWizard() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-panel p-4 shadow-panel">
        <div className="grid gap-3 md:grid-cols-5">
          {steps.map((step, index) => (
            <div key={step} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-caption text-subtle">
                <CheckCircle2 className="size-4 text-green" />
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

      <div className="rounded-xl border border-border bg-panel p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Upload className="size-4 text-green" /> Ready to Import
            </div>
            <p className="mt-2 text-small text-muted">
              All columns successfully mapped and validated. Prospects will be enriched and compliance checked upon import.
            </p>
          </div>
          <GateReasonBadge state="passed" label="Validated" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="default">
            Import prospects
          </Button>
          <Button variant="secondary">
            Save mapping
          </Button>
        </div>
      </div>
    </div>
  );
}
