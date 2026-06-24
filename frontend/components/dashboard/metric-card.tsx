import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  status = "Local demo",
  tone = "default",
  className,
}: {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  status?: string;
  tone?: "default" | "success" | "warning" | "locked";
  className?: string;
}) {
  const toneClass = {
    default: "bg-bluebg text-blue",
    success: "bg-goodbg text-green",
    warning: "bg-warnbg text-yellow",
    locked: "bg-panel2 text-muted",
  }[tone];

  const badgeVariant = tone === "success" ? "success" : tone === "warning" ? "warning" : tone === "locked" ? "locked" : "default";

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="space-y-0 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className={cn("flex size-10 items-center justify-center rounded-medium", toneClass)}>
            <Icon className="size-5" />
          </div>
          <Badge variant={badgeVariant} pulse={tone === "success" || tone === "warning" || tone === "default"}>{status}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <CardTitle className="text-small text-muted">{title}</CardTitle>
        <p className="mt-2 text-h2 text-text">{value}</p>
        <p className="mt-2 text-caption text-muted">{description}</p>
      </CardContent>
    </Card>
  );
}
