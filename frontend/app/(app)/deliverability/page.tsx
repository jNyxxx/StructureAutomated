import { DeliverabilityDashboard } from "@/components/deliverability/deliverability-dashboard";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";

export default function DeliverabilityPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Send safety dashboard"
        title="Deliverability"
        description="Read-only deliverability workspace using backend mock API data with fixture fallback. No DNS checks, mailbox provider calls, exports, recalculation actions, webhooks, or real sending are performed."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
          </>
        }
      />

      <LocalMockNotice />

      <DeliverabilityDashboard />
    </section>
  );
}
