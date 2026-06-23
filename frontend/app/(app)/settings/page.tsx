import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";

export default function SettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Account and workspace settings shell. Deeper settings screens remain local/mock or pending backend wiring."
      />
      <LocalMockNotice />
    </section>
  );
}
