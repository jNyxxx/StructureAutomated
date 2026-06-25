import { AlertTriangle, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { SuppressionTable } from "@/components/settings/suppression-table";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SuppressionSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="No-send controls" title="Suppression settings" description="Suppression create and reinstate use the backend mock API only. No real unsubscribe webhook, provider sync, export, privacy delete, real sending, or production action is enabled." actions={<><Badge variant="default">Local/mock MVP</Badge><Badge variant="locked">Provider sync locked</Badge></>} />
      <LocalMockNotice />
      <Card className="border-yellow/25 bg-warnbg/60"><CardHeader><div className="flex gap-3"><div className="flex size-10 items-center justify-center rounded-medium bg-warnbg text-yellow"><AlertTriangle className="size-5" /></div><div><CardTitle>Safe local/mock suppression actions only</CardTitle><CardDescription>Create and reinstate are backend mock API actions. Real delete, export, unsubscribe webhook persistence, provider sync, and production compliance automation remain disabled.</CardDescription></div></div></CardHeader><CardContent className="flex flex-wrap gap-2"><GateReasonBadge state="passed" label="Suppression mock actions" /><GateReasonBadge state="blocked" label="No provider sync" /><GateReasonBadge state="blocked" label="No real webhooks" /><GateReasonBadge state="blocked" label="Export locked" /></CardContent></Card>
      <SuppressionTable />
    </section>
  );
}
