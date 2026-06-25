import { OutcomesDashboard } from "@/components/outcomes/outcomes-dashboard";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";

export default function OutcomesPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Outcome intelligence"
        title="Outcomes and ROI"
        description="Read-only outcomes dashboard using backend mock API data with fixture fallback. No CRM, ads, payment, revenue, attribution, Stripe, provider integrations, or production analytics are connected."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
          </>
        }
      />

      <LocalMockNotice />

      <OutcomesDashboard />
    </section>
  );
}
