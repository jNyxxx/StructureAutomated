import { FileText } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";

export function ResearchArtifactCard({ title, description, state }: { title: string; description: string; state: "passed" | "warning" | "pending" | "blocked" }) {
  return (
    <div className="rounded-medium border border-border bg-panel2 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3">
          <div className="flex size-9 items-center justify-center rounded-small bg-violetbg text-violet">
            <FileText className="size-4" />
          </div>
          <div>
            <p className="text-small font-semibold text-text">{title}</p>
            <p className="mt-1 text-caption text-muted">{description}</p>
          </div>
        </div>
        <GateReasonBadge state={state} />
      </div>
    </div>
  );
}
