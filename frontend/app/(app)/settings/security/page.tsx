import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { SecurityPanel } from "@/components/settings/security-panel";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SecuritySettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Auth and sessions" title="Security settings" description="Manage authentication options, session lifespans, and MFA settings."  />

      <SecurityPanel />
    </section>
  );
}
