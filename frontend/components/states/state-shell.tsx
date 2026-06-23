import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface StateAction {
  label: string;
  onClick?: () => void;
  href?: string;
}

export interface StateShellProps {
  title: string;
  description: string;
  icon: LucideIcon;
  tone?: "default" | "success" | "warning" | "danger" | "locked" | "pending";
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
  children?: ReactNode;
  className?: string;
}

const toneClass = {
  default: "bg-bluebg text-blue",
  success: "bg-goodbg text-green",
  warning: "bg-warnbg text-yellow",
  danger: "bg-redbg text-red",
  locked: "bg-panel2 text-muted",
  pending: "bg-violetbg text-violet",
};

export function StateShell({
  title,
  description,
  icon: Icon,
  tone = "default",
  primaryAction,
  secondaryAction,
  children,
  className,
}: StateShellProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <div className={cn("flex size-12 shrink-0 items-center justify-center rounded-large", toneClass[tone])}>
            <Icon className="size-6" />
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle>{title}</CardTitle>
            <CardDescription className="mt-2 max-w-2xl">{description}</CardDescription>
          </div>
          {(primaryAction || secondaryAction) && (
            <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
              {secondaryAction}
              {primaryAction}
            </div>
          )}
        </div>
      </CardHeader>
      {children ? <CardContent>{children}</CardContent> : null}
    </Card>
  );
}
