import { PendingBackendPage } from "@/components/layout/pending-backend-page";

export default function SecuritySettingsPage() {
  return (
    <PendingBackendPage
      title="Security"
      description="Security and session controls are shown as a shell only. Clerk/auth boundaries remain unchanged and backend APIs are not expanded here."
    />
  );
}
