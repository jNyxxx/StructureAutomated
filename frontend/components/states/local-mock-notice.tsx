import { FlaskConical } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function LocalMockNotice({ className }: { className?: string }) {
  return (
    <aside
      className={cn(
        "rounded-xl border border-blue/25 bg-bluebg/70 p-4 text-small text-muted shadow-panel",
        className,
      )}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-bluebg text-blue">
            <FlaskConical className="size-5" />
          </div>
          <div>
            <p className="font-semibold text-text">Local/mock MVP only</p>
            <p className="mt-1 max-w-2xl">
              This shell supports design validation and safe local demos. It does not enable production, real sending, Stripe billing, SMS, webhooks, or live scraping.
            </p>
          </div>
        </div>
        <Badge variant="default">Demo safe</Badge>
      </div>
    </aside>
  );
}

export const LocalMockBanner = LocalMockNotice;
