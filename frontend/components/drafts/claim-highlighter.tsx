import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ClaimItem } from "./draft-sample-data";

export function ClaimHighlighter({ claims }: { claims: ClaimItem[] }) {
  if (claims.length === 0) {
    return (
      <div className="rounded-medium border border-green/25 bg-goodbg p-3 text-small text-muted">
        <div className="flex items-center gap-2 font-semibold text-text">
          <CheckCircle2 className="size-4 text-green" /> No unsupported claims in local/demo review.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {claims.map((claim) => (
        <div key={claim.id} className="rounded-medium border border-yellow/30 bg-warnbg p-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 size-4 text-yellow" />
              <div>
                <p className="text-small font-semibold text-text">{claim.text}</p>
                <p className="mt-1 text-caption text-muted">{claim.reason}</p>
              </div>
            </div>
            <Badge variant="warning">Needs regeneration</Badge>
          </div>
        </div>
      ))}
    </div>
  );
}
