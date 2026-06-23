import { PendingBackendPage } from "@/components/layout/pending-backend-page";

export default function SuppressionSettingsPage() {
  return (
    <PendingBackendPage
      title="Suppression"
      description="Suppression navigation is available. Suppress/reinstate actions stay locked until suppression APIs are mounted."
    />
  );
}
