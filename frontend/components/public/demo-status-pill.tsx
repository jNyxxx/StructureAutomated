import { Shield, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

export function DemoStatusPill({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "inline-flex flex-wrap items-center gap-2 rounded-pill border border-blue/20 bg-bluebg/40 px-3 py-1.5 text-caption font-semibold text-muted shadow-sm",
        className,
      )}
    >
      <span className="inline-flex items-center gap-1 text-blue">
        <Sparkles className="size-3" /> Sandbox Environment
      </span>
      <span className="h-1 w-1 rounded-pill bg-border2" />
      <span className="inline-flex items-center gap-1 text-subtle">
        <Shield className="size-3" /> Secure Tenant
      </span>
    </div>
  );
}
