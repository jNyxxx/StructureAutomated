import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Input({ className, type, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      type={type}
      className={cn(
        "as-focus-ring flex h-button-height w-full rounded-medium border border-border bg-panel2 px-3 py-2 text-small text-text shadow-sm transition-colors placeholder:text-subtle disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
