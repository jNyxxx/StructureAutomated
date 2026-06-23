import { FileSpreadsheet, UploadCloud } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";

export function CsvUploadDropzone() {
  return (
    <div className="rounded-xl border border-dashed border-blue/35 bg-bluebg/40 p-6 text-center shadow-panel">
      <div className="mx-auto flex size-14 items-center justify-center rounded-large bg-bluebg text-blue">
        <UploadCloud className="size-7" />
      </div>
      <h2 className="mt-4 text-h3 text-text">Upload CSV</h2>
      <p className="mx-auto mt-2 max-w-xl text-small text-muted">
        Visual-only dropzone. This slice does not upload files, persist imports, or call backend import APIs.
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <span className="inline-flex items-center gap-2 rounded-pill border border-border bg-panel2 px-3 py-2 text-caption text-muted">
          <FileSpreadsheet className="size-3.5" /> prospects_demo.csv
        </span>
        <GateReasonBadge state="pending" label="Upload API pending" />
      </div>
    </div>
  );
}
