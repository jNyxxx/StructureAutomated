import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { CompliancePanel } from "@/components/settings/compliance-panel";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ComplianceSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Compliance controls" title="Compliance settings" description="Local/mock compliance profile from the backend mock API. Profile update is mock-only; real webhooks, provider sync, live sending, and production compliance automation remain disabled." actions={<><Badge variant="default">Local/mock MVP</Badge><Badge variant="locked">Live sending review pending</Badge></>} />
      <LocalMockNotice />
      <Card className="border-yellow/25 bg-warnbg/60"><CardHeader><div className="flex gap-3"><div className="flex size-10 items-center justify-center rounded-medium bg-warnbg text-yellow"><AlertTriangle className="size-5" /></div><div><CardTitle>Compliance review required before live sending</CardTitle><CardDescription>This UI does not enable live sends, real webhooks, provider calls, provider sync, or production legal compliance automation.</CardDescription></div></div></CardHeader><CardContent className="flex flex-wrap gap-2"><GateReasonBadge state="blocked" label="No real sending" /><GateReasonBadge state="passed" label="Compliance mock update" /><GateReasonBadge state="warning" label="Manual approval required" /><GateReasonBadge state="blocked" label="No provider sync" /></CardContent></Card>
      <CompliancePanel />
    </section>
  );
}
