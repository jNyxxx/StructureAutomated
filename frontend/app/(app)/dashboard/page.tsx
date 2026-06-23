import { PageHeader } from "@/components/layout/page-header";
import { EmptyState, LocalMockNotice } from "@/components/states";

export default function DashboardPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Command center"
        title="Dashboard"
        description="Dashboard cards and metrics are intentionally deferred. This shell preserves navigation and safe local/mock MVP behavior."
      />
      <LocalMockNotice />
      <EmptyState
        title="Dashboard metrics pending"
        description="Metrics will be wired after the matching backend dashboard/outcomes APIs are exposed."
      />
    </section>
  );
}
