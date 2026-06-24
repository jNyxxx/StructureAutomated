import { Download, Lock, Trash2 } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";

export function PrivacyRequestPanel() {
  return (
    <BentoCard title="Privacy requests" description="Export/delete/vector purge request shells. No backend privacy workflow is called." badge="Pending backend">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <p className="text-small font-semibold text-text">Export request</p>
          <p className="mt-1 text-caption text-muted">Download export is pending backend API.</p>
          <Button disabled className="mt-3"><Download className="size-4" /> Request export</Button>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <p className="text-small font-semibold text-text">Deletion request</p>
          <p className="mt-1 text-caption text-muted">Soft delete first; hard delete after 30 days.</p>
          <Button disabled className="mt-3" variant="secondary"><Trash2 className="size-4" /> Request delete</Button>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <p className="text-small font-semibold text-text">Knowledge/vector purge</p>
          <p className="mt-1 text-caption text-muted">Vector and knowledge purge API pending.</p>
          <Button disabled className="mt-3" variant="locked"><Lock className="size-4" /> Purge pending</Button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <GateReasonBadge state="pending" label="Export API pending" />
        <GateReasonBadge state="pending" label="Delete API pending" />
        <GateReasonBadge state="blocked" label="No fake download" />
      </div>
    </BentoCard>
  );
}
