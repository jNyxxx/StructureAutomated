import { ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";

export function AuditRedactedDetails({ details }: { details: Record<string, string> }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-medium border border-green/25 bg-goodbg p-3 text-small text-muted">
        <ShieldAlert className="size-4 text-green" /> Secrets, tokens, raw emails, tenant IDs, and sessions are redacted before display.
      </div>
      <div className="rounded-medium border border-border bg-panel2 p-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="text-small font-semibold text-text">Redacted JSON/details viewer</p>
          <GateReasonBadge state="passed" label="redacted" />
        </div>
        <pre className="max-h-72 overflow-auto rounded-small bg-panel p-3 text-caption text-muted">
{JSON.stringify(details, null, 2)}
        </pre>
      </div>
    </div>
  );
}
