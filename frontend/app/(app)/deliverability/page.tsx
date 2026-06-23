import { PendingBackendPage } from "@/components/layout/pending-backend-page";

export default function DeliverabilityPage() {
  return (
    <PendingBackendPage
      title="Deliverability"
      description="Mailbox and warm-up navigation is visible for the local/mock shell. No real sending, DNS, provider, or throttle APIs are wired."
    />
  );
}
