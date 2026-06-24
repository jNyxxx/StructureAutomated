"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CircleCheck, Lock, Terminal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  appNavSections,
  getNavStatusLabel,
  isActiveRoute,
  type NavStatus,
} from "@/lib/navigation";
import { cn } from "@/lib/utils";

function statusVariant(status: NavStatus) {
  if (status === "available") return "success";
  if (status === "demo") return "default";
  if (status === "pending-backend") return "warning";
  return "locked";
}

export function AppSidebar({ className, onNavigate }: { className?: string; onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <aside className={cn("flex h-full flex-col border-r border-border bg-panel/95", className)} aria-label="Application sidebar">
      <div className="flex h-topbar items-center gap-3 px-5">
        <div className="flex size-10 items-center justify-center rounded-medium bg-bluebg text-blue">
          <Terminal className="size-5" />
        </div>
        <div className="min-w-0 group">
          <p className="truncate text-small font-bold text-text group-hover:whitespace-normal group-hover:overflow-visible transition-all duration-200">AutomatedStructure</p>
          <p className="truncate text-caption text-muted group-hover:whitespace-normal group-hover:overflow-visible transition-all duration-200">Enterprise Management Console</p>
        </div>
      </div>



      <Separator />

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Primary app navigation">
        {appNavSections.map((section) => (
          <div key={section.label}>
            <p className="px-2 pb-2 text-caption font-semibold uppercase tracking-wide text-subtle">
              {section.label}
            </p>
            <div className="space-y-1">
              {section.items.map((item) => {
                const active = isActiveRoute(pathname, item.href);
                const Icon = item.icon;
                const locked = item.status === "pending-backend" || item.status === "locked";

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onNavigate}
                    className={cn(
                      "group flex items-center gap-3 rounded-medium px-3 py-2.5 text-small transition-colors",
                      active
                        ? "bg-blue text-white shadow-sm"
                        : "text-muted hover:bg-panel2 hover:text-text",
                    )}
                    aria-current={active ? "page" : undefined}
                    aria-label={`${item.label}: ${getNavStatusLabel(item.status)}. ${item.description}`}
                    title={`${item.label}: ${getNavStatusLabel(item.status)}. ${item.description}`}
                  >
                    <Icon className="size-4 shrink-0" />
                    <span className="min-w-0 flex-1 truncate group-hover:whitespace-normal group-hover:overflow-visible transition-all duration-200">{item.label}</span>
                    {locked ? (
                      <><Lock className={cn("size-3 shrink-0", active ? "text-white" : "text-subtle")} /><span className="sr-only">{getNavStatusLabel(item.status)}</span></>
                    ) : (
                      <span
                        className={cn(
                          "hidden rounded-pill border px-1.5 py-0.5 text-[10px] font-semibold lg:inline-flex",
                          active ? "border-white/30 text-white" : "border-border text-subtle",
                        )}
                      >
                        {getNavStatusLabel(item.status)}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <div className="flex items-center justify-between gap-2 rounded-medium bg-panel2 p-3">
          <div>
            <p className="text-small font-semibold text-text">Security Shield</p>
            <p className="text-caption text-muted">Forced multi-tenant RLS active</p>
          </div>
          <Badge variant="success">Secured</Badge>
        </div>
      </div>
    </aside>
  );
}
