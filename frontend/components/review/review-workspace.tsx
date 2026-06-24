import { DraftPreview } from "@/components/drafts/draft-preview";
import { EvidenceList } from "@/components/drafts/evidence-list";
import { GroundednessPanel } from "@/components/drafts/groundedness-panel";
import { ClaimHighlighter } from "@/components/drafts/claim-highlighter";
import { DraftGatePanel } from "@/components/drafts/draft-gate-panel";
import { BentoCard } from "@/components/dashboard/bento-card";
import { ReviewActivityTimeline } from "./review-activity-timeline";
import { ReviewDecisionPanel } from "./review-decision-panel";
import { SendReadinessPanel } from "./send-readiness-panel";
import type { ReviewItem } from "./review-sample-data";

export function ReviewWorkspace({ item }: { item: ReviewItem }) {
  return (
    <div className="space-y-4">
      <DraftPreview draft={item.draft} />
      <div className="grid gap-4 xl:grid-cols-2">
        <BentoCard title="Evidence/source list" description="Verified context sources and grounding materials." badge="Verified">
          <EvidenceList evidence={item.draft.evidence} />
        </BentoCard>
        <BentoCard title="Claim highlights" description="Unsupported claims block approval and require regeneration." badge="Claims">
          <ClaimHighlighter claims={item.draft.unsupportedClaims} />
        </BentoCard>
      </div>
      <GroundednessPanel draft={item.draft} />
      <DraftGatePanel draft={item.draft} />
      <ReviewDecisionPanel item={item} />
      <SendReadinessPanel item={item} />
      <ReviewActivityTimeline item={item} />
    </div>
  );
}
