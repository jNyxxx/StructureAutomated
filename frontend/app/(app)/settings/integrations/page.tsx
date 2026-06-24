import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { IntegrationCard } from "@/components/settings/integration-card";
import { integrations } from "@/components/settings/settings-sample-data";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function IntegrationsSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Provider connections" title="Integrations" description="Future provider connection cards only. No OAuth, provider, SMS, Ads, GBP, scraping, or webhook calls are wired." actions={<><Badge variant="default">Local/mock MVP</Badge><Badge variant="locked">Providers disabled</Badge></>} />
      <LocalMockNotice />
      <Card className="border-yellow/25 bg-warnbg/60"><CardHeader><div className="flex gap-3"><div className="flex size-10 items-center justify-center rounded-medium bg-warnbg text-yellow"><AlertTriangle className="size-5" /></div><div><CardTitle>No real provider/OAuth calls</CardTitle><CardDescription>SMS/Twilio, Google/Meta Ads, GBP, live scraping, and webhooks are post-MVP or disabled.</CardDescription></div></div></CardHeader><CardContent className="flex flex-wrap gap-2"><GateReasonBadge state="blocked" label="No OAuth" /><GateReasonBadge state="blocked" label="No SMS/Twilio" /><GateReasonBadge state="blocked" label="No Ads/GBP" /><GateReasonBadge state="blocked" label="No live scraping" /></CardContent></Card>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{integrations.map((item) => <IntegrationCard key={item.name} {...item} />)}</div>
    </section>
  );
}
