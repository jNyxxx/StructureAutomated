import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function DemoStatusPill({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "inline-flex flex-wrap items-center gap-2 rounded-pill border border-green/25 bg-goodbg/70 px-3 py-2 text-caption font-semibold text-muted shadow-panel",
        className,
      )}
    >
      <span className="inline-flex items-center gap-1.5 text-green">
        <ShieldCheck className="size-3.5" /> Workspace Active
      </span>
      <span className="h-1 w-1 rounded-pill bg-border2" />
      <span className="inline-flex items-center gap-1.5 text-subtle">
        Multi-tenant isolation active
      </span>
      <Badge variant="success">Secured</Badge>
    </div>
  );
}
