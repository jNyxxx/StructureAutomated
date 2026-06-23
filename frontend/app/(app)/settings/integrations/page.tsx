import { PendingBackendPage } from "@/components/layout/pending-backend-page";

export default function IntegrationsSettingsPage() {
  return (
    <PendingBackendPage
      title="Integrations"
      description="Integration credentials and provider connections are represented as a shell only. No secrets, provider calls, or webhooks are wired here."
    />
  );
}
