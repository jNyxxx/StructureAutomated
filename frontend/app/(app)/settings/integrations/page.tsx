import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { IntegrationCard } from "@/components/settings/integration-card";
import { integrations } from "@/components/settings/settings-sample-data";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function IntegrationsSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Provider connections" title="Integrations" description="Configure third-party connectors and APIs."  />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{integrations.map((item) => <IntegrationCard key={item.name} {...item} />)}</div>
    </section>
  );
}
