import { FlaskConical } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function LocalMockNotice({ className }: { className?: string }) {
  return (
    <aside className="sr-only">
      <p>Local/mock MVP only</p>
      <p>
        This shell supports design validation and safe local demos. It does not enable production, real sending, Stripe billing, SMS, webhooks, or live scraping.
      </p>
      <span>Demo safe</span>
    </aside>
  );
}

export const LocalMockBanner = LocalMockNotice;
