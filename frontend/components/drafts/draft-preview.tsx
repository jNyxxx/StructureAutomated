import { Mail, ShieldAlert } from "lucide-react";

import { StatusBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import type { DraftRow } from "./draft-sample-data";

export function DraftPreview({ draft }: { draft: DraftRow }) {
  return (
    <BentoCard title="Draft preview" description="Grounded message preview and verification status." badge="Preview">
      <div className="space-y-4">
        <div className="rounded-medium border border-border bg-panel2 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-caption text-subtle">Subject</p>
              <h2 className="mt-1 text-h3 text-text">{draft.subject}</h2>
            </div>
            <StatusBadge status={draft.status} />
          </div>
          <div className="mt-4 rounded-medium border border-border bg-panel p-4 text-small leading-6 text-muted">
            {draft.body}
          </div>
        </div>
        {draft.suppressedContact ? (
          <div className="flex items-center gap-2 rounded-medium border border-red/25 bg-redbg p-3 text-small text-muted">
            <ShieldAlert className="size-4 text-red" /> Contact suppressed: outreach actions blocked.
          </div>
        ) : null}
        <div className="flex items-center gap-2 text-caption text-subtle">
          <Mail className="size-3.5" /> Outbound queue monitored.
        </div>
      </div>
    </BentoCard>
  );
}
