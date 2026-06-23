import { AlertTriangle, Archive, CheckCircle2, Clock3, CopyX, Loader2, Send, XCircle } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type ProductStatus =
  | "draft_generated"
  | "blocked"
  | "needs_regeneration"
  | "archived"
  | "pending_review"
  | "approved"
  | "rejected"
  | "regeneration_requested"
  | "mock_sent"
  | "duplicate"
  | "mock_queued"
  | "scheduled"
  | "queued"
  | "skipped"
  | "canceled"
  | "failed";

const statusConfig: Record<ProductStatus, { label: string; variant: BadgeProps["variant"]; icon: typeof CheckCircle2 }> = {
  draft_generated: { label: "Draft generated", variant: "default", icon: CheckCircle2 },
  blocked: { label: "Blocked", variant: "locked", icon: XCircle },
  needs_regeneration: { label: "Needs regeneration", variant: "warning", icon: AlertTriangle },
  archived: { label: "Archived", variant: "locked", icon: Archive },
  pending_review: { label: "Pending review", variant: "warning", icon: Clock3 },
  approved: { label: "Approved", variant: "success", icon: CheckCircle2 },
  rejected: { label: "Rejected", variant: "danger", icon: XCircle },
  regeneration_requested: { label: "Regeneration requested", variant: "warning", icon: Loader2 },
  mock_sent: { label: "Mock sent", variant: "success", icon: Send },
  duplicate: { label: "Duplicate", variant: "locked", icon: CopyX },
  mock_queued: { label: "Mock queued", variant: "default", icon: Clock3 },
  scheduled: { label: "Scheduled", variant: "default", icon: Clock3 },
  queued: { label: "Queued", variant: "default", icon: Clock3 },
  skipped: { label: "Skipped", variant: "locked", icon: Archive },
  canceled: { label: "Canceled", variant: "locked", icon: XCircle },
  failed: { label: "Failed", variant: "danger", icon: XCircle },
};

export function StatusBadge({ status, className }: { status: ProductStatus; className?: string }) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn("gap-1.5", className)}>
      <Icon className="size-3.5" />
      {config.label}
    </Badge>
  );
}
