import { AlertTriangle, ScrollText } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { DataRetentionPanel } from "@/components/privacy/data-retention-panel";
import { PrivacyPostureCard } from "@/components/privacy/privacy-posture-card";
import { PrivacyRequestPanel } from "@/components/privacy/privacy-request-panel";
import { PrivacyTimeline } from "@/components/privacy/privacy-timeline";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function PrivacyPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Privacy operations"
        title="Privacy"
        description="Privacy export, deletion, retention, suppression-minimum, and vector purge workflow shell. Backend privacy APIs are pending."
        actions={<><Badge variant="default">Local/mock MVP</Badge><Badge variant="locked">Production not approved</Badge></>}
      />
      <LocalMockNotice />
      <Card className="border-yellow/25 bg-warnbg/60">
        <CardHeader><div className="flex gap-3"><div className="flex size-10 items-center justify-center rounded-medium bg-warnbg text-yellow"><AlertTriangle className="size-5" /></div><div><CardTitle>Pending backend privacy APIs</CardTitle><CardDescription>Export, delete, download, deletion confirmation, and knowledge/vector purge actions are disabled until backend workflows exist.</CardDescription></div></div></CardHeader>
        <CardContent className="flex flex-wrap gap-2"><GateReasonBadge state="pending" label="Export API pending" /><GateReasonBadge state="pending" label="Delete API pending" /><GateReasonBadge state="pending" label="Vector purge pending" /><GateReasonBadge state="blocked" label="No fake completion" /></CardContent>
      </Card>
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
