import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const badgeVariants = cva(
  "inline-flex items-center rounded-pill border px-2.5 py-1 text-caption font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-blue/30 bg-bluebg text-blue",
        success: "border-green/30 bg-goodbg text-green",
        warning: "border-yellow/30 bg-warnbg text-yellow",
        danger: "border-red/30 bg-redbg text-red",
        violet: "border-violet/30 bg-violetbg text-violet",
        locked: "border-border bg-panel2 text-muted",
        outline: "border-border bg-transparent text-muted",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  pulse?: boolean;
}

export function Badge({ className, variant, pulse, ...props }: BadgeProps) {
  const pulseClass = pulse
    ? {
        default: "ambient-ring-info",
        success: "ambient-ring-success",
        warning: "ambient-ring-warning",
        danger: "",
        violet: "",
        locked: "",
        outline: "",
      }[variant || "default"]
    : "";

  return <div className={cn(badgeVariants({ variant }), pulseClass, className)} {...props} />;
}
