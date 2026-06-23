import { ShieldAlert, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import type { ProspectRow } from "./prospect-sample-data";

export function ProspectDetailDrawer({ prospect }: { prospect: ProspectRow }) {
  const blocked = prospect.suppressionStatus === "suppressed" || prospect.campaignStatus === "blocked";

  return (
    <div className="space-y-4 text-small text-muted">
      <div className="flex items-center gap-2 rounded-medium border border-blue/25 bg-bluebg p-3">
        <ShieldCheck className="size-4 text-blue" /> Read-only local/demo prospect. No backend detail API is wired.
      </div>
      {blocked ? (
        <div className="flex items-center gap-2 rounded-medium border border-red/25 bg-redbg p-3">
          <ShieldAlert className="size-4 text-red" /> Suppression/compliance warning: keep outreach actions blocked.
        </div>
      ) : null}
      <dl className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Company</dt>
          <dd>{prospect.company}</dd>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Segment</dt>
          <dd>{prospect.marketSegment}</dd>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Source</dt>
          <dd>{prospect.source}</dd>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Safe notes</dt>
          <dd>{prospect.safeNotes}</dd>
        </div>
      </dl>
      <div className="flex flex-wrap gap-2">
        <GateReasonBadge state="pending" label="Enrich API pending" />
        <GateReasonBadge state="blocked" label="No real sending" />
        <GateReasonBadge state="pending" label="Campaign API pending" />
      </div>
    </div>
  );
}
