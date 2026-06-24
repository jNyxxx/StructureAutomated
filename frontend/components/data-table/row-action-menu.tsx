"use client";

import { MoreHorizontal } from "lucide-react";
import { useState } from "react";

import { GateReasonBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { RowAction } from "./types";

export function RowActionMenu<TData>({ row, actions }: { row: TData; actions: RowAction<TData>[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative flex justify-end">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Open row actions"
        onClick={() => setOpen((value) => !value)}
      >
        <MoreHorizontal className="size-4" />
      </Button>
      {open ? (
        <div
          role="menu"
          className={cn(
            "absolute right-0 top-10 z-20 w-48 overflow-hidden rounded-medium border border-border bg-panel shadow-glow",
          )}
        >
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              role="menuitem"
              disabled={action.disabled || action.pendingBackend}
              onClick={() => {
                action.onSelect?.(row);
                setOpen(false);
              }}
              title={action.pendingBackend ? "Backend API pending" : action.disabled ? "Action disabled in local/mock MVP" : action.label}
              className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-small text-muted hover:bg-panel2 hover:text-text disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span>{action.label}</span>
              {action.pendingBackend ? <GateReasonBadge state="pending" label="API" /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
