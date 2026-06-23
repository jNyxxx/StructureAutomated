import Link from "next/link";
import { Download, FilePlus2, Lock, Send, Sparkles, Upload, UserCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";

const actions = [
  { label: "Import CSV", href: "/prospects/import", icon: Upload, reason: "Import API pending" },
  { label: "Create campaign", href: "/campaigns", icon: FilePlus2, reason: "Campaign API pending" },
  { label: "Generate draft", href: "/ai-drafts", icon: Sparkles, reason: "Draft API pending" },
  { label: "Approve draft", href: "/review-queue", icon: UserCheck, reason: "Review API pending" },
  { label: "Mock send", href: "/deliverability", icon: Send, reason: "Send gate not wired" },
  { label: "Export", href: "/outcomes", icon: Download, reason: "Export API pending" },
];

export function QuickActions() {
  return (
    <BentoCard title="Locked quick actions" description="Actions are visible for navigation but disabled by pending backend APIs." badge="Pending backend">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <div key={action.label} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-panel text-muted">
                  <Icon className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-small font-semibold text-text">{action.label}</p>
                  <p className="text-caption text-muted">{action.reason}</p>
                </div>
                <Lock className="size-4 text-subtle" />
              </div>
              <div className="mt-3 flex items-center justify-between gap-3">
                <GateReasonBadge state="blocked" label="Locked" />
                <Button asChild variant="ghost" size="sm">
                  <Link href={action.href}>View shell</Link>
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </BentoCard>
  );
}
