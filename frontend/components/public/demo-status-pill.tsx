import { FlaskConical, Lock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function DemoStatusPill({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "inline-flex flex-wrap items-center gap-2 rounded-pill border border-blue/25 bg-bluebg/70 px-3 py-2 text-caption font-semibold text-muted shadow-panel",
        className,
      )}
    >
      <span className="inline-flex items-center gap-1.5 text-blue">
        <FlaskConical className="size-3.5" /> Local/mock MVP
      </span>
      <span className="h-1 w-1 rounded-pill bg-border2" />
      <span className="inline-flex items-center gap-1.5 text-subtle">
        <Lock className="size-3.5" /> Production not approved
      </span>
      <Badge variant="locked">No live sending</Badge>
    </div>
  );
}
