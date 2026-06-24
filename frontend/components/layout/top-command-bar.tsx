"use client";

import { Bell, ChevronDown, Command, Lock, Search, User } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { readOnlyBillingStatus } from "@/components/billing-banner";
import { BackendStatusBadge } from "@/components/layout/backend-status";
import { useTenantContext } from "@/lib/tenant-context";
import { cn } from "@/lib/utils";

export function TopCommandBar({
  className,
  mobileNav,
}: {
  className?: string;
  mobileNav?: ReactNode;
}) {
  const tenant = useTenantContext();

  return (
    <TooltipProvider>
      <header
        className={cn(
          "sticky top-0 z-30 flex min-h-topbar items-center gap-3 border-b border-border bg-bg/85 px-4 backdrop-blur-xl lg:px-6",
          className,
        )}
      >
        <div className="lg:hidden">{mobileNav}</div>

        <div className="hidden min-w-0 flex-col lg:flex">
          <p className="text-caption font-semibold uppercase tracking-wide text-subtle">Command center</p>
          <h1 className="truncate text-small font-bold text-text">Secure tenant console</h1>
        </div>

        <Separator orientation="vertical" className="hidden h-8 lg:block" />

        <div className="min-w-0 flex-1">
          <label className="sr-only" htmlFor="global-command-search">
            Search commands
          </label>
          <div className="relative max-w-xl">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle" />
            <Input
              id="global-command-search"
              className="h-10 rounded-pill bg-panel/80 pl-9 pr-20"
              placeholder="Search routes, prospects, campaigns..."
              aria-describedby="command-search-help"
            />
            <div className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded-small border border-border px-1.5 py-0.5 text-[10px] font-semibold text-subtle sm:flex">
              <Command className="size-3" />K
            </div>
          </div>
          <p id="command-search-help" className="sr-only">
            Search shell only. Backend search APIs are not mounted yet.
          </p>
        </div>

        <div className="hidden items-center gap-2 xl:flex">
          <BackendStatusBadge />
          <Badge variant="default">Local MVP</Badge>
          <Badge variant="locked">No production</Badge>
        </div>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="secondary" size="sm" className="hidden max-w-[220px] justify-start gap-2 md:inline-flex" aria-label="Tenant switcher shell" title="Tenant switcher shell; backend tenant switch API is pending">
              <span className="size-2 rounded-pill bg-yellow" />
              <span className="truncate">
                {tenant.isConfirmed ? tenant.role ?? "Tenant confirmed" : tenant.selectedTenantId ? "Tenant pending" : "Select tenant"}
              </span>
              <ChevronDown className="size-4 text-subtle" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            Tenant switcher shell. Status: {tenant.status}. Tenant confirmation comes from /auth/me.
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="secondary" size="icon" aria-label="Billing and access status">
              <Lock className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            Billing: {readOnlyBillingStatus.mode.replace("_", " ")} — costly/outbound actions locked.
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Notifications and activity">
              <Bell className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Notifications/activity shell only.</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="User menu">
              <User className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>User menu shell. Auth state remains protected by current gate.</TooltipContent>
        </Tooltip>
      </header>
    </TooltipProvider>
  );
}
