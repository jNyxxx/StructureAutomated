import { AlertTriangle, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { SuppressionTable } from "@/components/settings/suppression-table";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SuppressionSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="No-send controls" title="Suppression settings" description="Demo-safe suppression table only. Delete/export/unsubscribe persistence is not wired." actions={<><Badge variant="default">Local/mock MVP</Badge><Button disabled><ShieldAlert className="size-4" /> Add suppression locked</Button></>} />
      <LocalMockNotice />
      <Card className="border-yellow/25 bg-warnbg/60"><CardHeader><div className="flex gap-3"><div className="flex size-10 items-center justify-center rounded-medium bg-warnbg text-yellow"><AlertTriangle className="size-5" /></div><div><CardTitle>Suppression persistence pending</CardTitle><CardDescription>No real delete, export, unsubscribe, or suppression mutation is persisted from this UI.</CardDescription></div></div></CardHeader><CardContent className="flex flex-wrap gap-2"><GateReasonBadge state="blocked" label="No-send enforced visually" /><GateReasonBadge state="pending" label="Suppression API pending" /><GateReasonBadge state="blocked" label="Export locked" /></CardContent></Card>
      <SuppressionTable />
    </section>
  );
}
