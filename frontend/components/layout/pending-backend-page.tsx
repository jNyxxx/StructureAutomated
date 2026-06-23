import { PendingBackendState, LocalMockNotice } from "@/components/states";
import { PageHeader } from "@/components/layout/page-header";

export function PendingBackendPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Local/mock MVP"
        title={title}
        description={description}
      />
      <PendingBackendState
        title="Pending backend wiring"
        description="This route is visible for navigation and design validation. The matching HTTP API is not mounted yet, so create, update, send, export, billing, provider, and destructive actions remain locked."
      />
      <LocalMockNotice />
    </section>
  );
}
