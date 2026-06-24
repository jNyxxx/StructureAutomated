import { AlertTriangle, ScrollText } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { DataRetentionPanel } from "@/components/privacy/data-retention-panel";
import { PrivacyPostureCard } from "@/components/privacy/privacy-posture-card";
import { PrivacyRequestPanel } from "@/components/privacy/privacy-request-panel";
import { PrivacyTimeline } from "@/components/privacy/privacy-timeline";
import { PageHeader } from "@/components/layout/page-header";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function PrivacyPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Privacy operations"
        title="Privacy"
        description="Manage user data exports, deletion requests, and retention policies."
        
      />

      <PrivacyPostureCard />
      <div className="grid gap-4 xl:grid-cols-2"><DataRetentionPanel /><PrivacyTimeline /></div>
      <PrivacyRequestPanel />
      <BentoCard title="Audit trail links" description="Privacy workflows must emit redacted audit events with request and correlation IDs." badge="Audit shell">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3"><div className="flex items-center gap-2 text-small font-semibold text-text"><ScrollText className="size-4 text-blue" /> Export requested</div><p className="mt-2 text-caption text-muted">Would link to audit trail after backend implementation.</p></div>
          <div className="rounded-medium border border-border bg-panel2 p-3"><div className="flex items-center gap-2 text-small font-semibold text-text"><ScrollText className="size-4 text-yellow" /> Deletion staged</div><p className="mt-2 text-caption text-muted">Soft delete and 30-day hard-delete window must be auditable.</p></div>
          <div className="rounded-medium border border-border bg-panel2 p-3"><div className="flex items-center gap-2 text-small font-semibold text-text"><ScrollText className="size-4 text-red" /> Purge pending</div><p className="mt-2 text-caption text-muted">Vector/knowledge purge evidence is pending backend APIs.</p></div>
        </div>
      </BentoCard>
    </section>
  );
}
