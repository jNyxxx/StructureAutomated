import { PendingBackendPage } from "@/components/layout/pending-backend-page";

export default function CampaignsPage() {
  return (
    <PendingBackendPage
      title="Campaigns"
      description="Campaign navigation is ready, but create/run/send actions remain locked until campaign and send-gate HTTP APIs are mounted."
    />
  );
}
