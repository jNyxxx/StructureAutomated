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
        Local/mock CSV preview. The confirmation step submits sample CSV text to the backend mock import API only.
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <span className="inline-flex items-center gap-2 rounded-pill border border-border bg-panel2 px-3 py-2 text-caption text-muted">
          <FileSpreadsheet className="size-3.5" /> prospects_demo.csv
        </span>
        <GateReasonBadge state="passed" label="Backend mock import" />
      </div>
    </div>
  );
}
