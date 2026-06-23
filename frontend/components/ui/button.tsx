import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "as-focus-ring inline-flex h-button-height shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-medium px-4 text-small font-semibold transition-colors disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-blue text-white shadow-glow hover:bg-blue2",
        secondary: "border border-border bg-panel2 text-text hover:bg-surface-light",
        ghost: "text-muted hover:bg-panel2 hover:text-text",
        destructive: "bg-red text-white hover:bg-red/90",
        outline: "border border-border bg-transparent text-text hover:bg-panel2",
        locked: "border border-border bg-panel text-muted hover:bg-panel",
      },
      size: {
        default: "h-button-height px-4",
        sm: "h-9 rounded-small px-3 text-caption",
        lg: "h-12 rounded-large px-5 text-body",
        icon: "h-button-height w-button-height px-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";

  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
