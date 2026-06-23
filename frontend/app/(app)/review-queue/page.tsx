import { PendingBackendPage } from "@/components/layout/pending-backend-page";

export default function ReviewQueuePage() {
  return (
    <PendingBackendPage
      title="Review Queue"
      description="Human review navigation is visible. Approval, rejection, edit, and scheduling actions stay locked until review APIs are mounted."
    />
  );
}
