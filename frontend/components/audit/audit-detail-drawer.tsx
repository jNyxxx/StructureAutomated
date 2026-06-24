import { Link2, ScrollText } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { AuditRedactedDetails } from "./audit-redacted-details";
import type { AuditRow } from "./audit-sample-data";

export function AuditDetailDrawer({ row }: { row: AuditRow }) {
  return (
    <div className="space-y-4 text-small text-muted">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex items-center gap-2 font-semibold text-text"><Link2 className="size-4 text-blue" /> Request ID</div>
          <p className="mt-1 break-all text-caption">{row.requestId}</p>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <div className="flex items-center gap-2 font-semibold text-text"><Link2 className="size-4 text-violet" /> Correlation ID</div>
          <p className="mt-1 break-all text-caption">{row.correlationId}</p>
        </div>
      </div>
      <AuditRedactedDetails details={row.redactedDetails} />
      <div className="rounded-medium border border-border bg-panel2 p-3">
        <div className="flex items-center gap-2 font-semibold text-text"><ScrollText className="size-4 text-yellow" /> Retention and support access note</div>
        <p className="mt-1 text-caption">Audit retention is for accountability. Support access must be explicit, time-bound, and audited before production.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <GateReasonBadge state="pending" label="Detail API pending" />
        <GateReasonBadge state="blocked" label="Export locked" />
      </div>
    </div>
  );
}
