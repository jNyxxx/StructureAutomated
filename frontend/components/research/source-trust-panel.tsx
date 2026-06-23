import { ShieldCheck, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";

export function SourceTrustPanel() {
  return (
    <BentoCard title="Source trust indicators" description="Demo-only trust states. No live scraping, enrichment, or embeddings provider calls occur." badge="Trust shell">
      <div className="space-y-3">
        <div className="rounded-medium border border-green/25 bg-goodbg p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ShieldCheck className="size-4 text-green" /> Approved local knowledge chunk
            </div>
            <GateReasonBadge state="passed" />
          </div>
        </div>
        <div className="rounded-medium border border-yellow/30 bg-warnbg p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ShieldAlert className="size-4 text-yellow" /> Incomplete external signal
            </div>
            <GateReasonBadge state="warning" />
          </div>
        </div>
        <div className="rounded-medium border border-red/25 bg-redbg p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ShieldAlert className="size-4 text-red" /> Live scraper/provider source
            </div>
            <GateReasonBadge state="blocked" label="Disabled" />
          </div>
        </div>
      </div>
    </BentoCard>
  );
}
