import { PendingBackendPage } from "@/components/layout/pending-backend-page";

export default function AiDraftsPage() {
  return (
    <PendingBackendPage
      title="AI Drafts"
      description="AI draft navigation is available. Groundedness, prompt-injection, re-grounding, and review actions remain backend-enforced and unavailable here."
    />
  );
}
