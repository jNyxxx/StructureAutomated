import { Lock } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function LockedFeatureOverlay({
  title = "Feature locked",
  description = "This capability is blocked by permission, billing, or pending backend wiring.",
  children,
  actionLabel,
  className,
}: {
  title?: string;
  description?: string;
  children?: ReactNode;
  actionLabel?: string;
  className?: string;
}) {
  return (
    <div className={cn("relative overflow-hidden rounded-xl border border-border bg-panel", className)}>
      <div className="pointer-events-none opacity-35 blur-[1px]">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center bg-bg/70 p-6 backdrop-blur-sm">
        <div className="max-w-md rounded-xl border border-border bg-panel p-card-padding text-center shadow-glow">
          <div className="mx-auto flex size-12 items-center justify-center rounded-large bg-panel2 text-muted">
            <Lock className="size-6" />
          </div>
          <Badge variant="locked" className="mt-4">Locked</Badge>
          <h3 className="mt-4 text-h3 text-text">{title}</h3>
          <p className="mt-2 text-small text-muted">{description}</p>
          {actionLabel ? <Button className="mt-5" variant="secondary">{actionLabel}</Button> : null}
        </div>
      </div>
    </div>
  );
}
