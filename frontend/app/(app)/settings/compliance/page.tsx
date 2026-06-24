import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { CompliancePanel } from "@/components/settings/compliance-panel";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ComplianceSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Compliance controls" title="Compliance settings" description="Manage unsubscribe links, suppression lists, and compliance profiles."  />

      <CompliancePanel />
    </section>
  );
}
