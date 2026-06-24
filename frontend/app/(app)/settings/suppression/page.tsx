import { AlertTriangle, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { SuppressionTable } from "@/components/settings/suppression-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SuppressionSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="No-send controls" title="Suppression settings" description="Manage global suppression lists for outreach." actions={<Button disabled><ShieldAlert className="size-4" /> Add suppression locked</Button>} />

      <SuppressionTable />
    </section>
  );
}
