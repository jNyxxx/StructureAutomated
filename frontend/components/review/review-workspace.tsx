"use client";

import { useCallback, useEffect, useState } from "react";

import { DraftPreview } from "@/components/drafts/draft-preview";
import { EvidenceList } from "@/components/drafts/evidence-list";
import { GroundednessPanel } from "@/components/drafts/groundedness-panel";
import { ClaimHighlighter } from "@/components/drafts/claim-highlighter";
import { DraftGatePanel } from "@/components/drafts/draft-gate-panel";
import { BentoCard } from "@/components/dashboard/bento-card";
import { ErrorState } from "@/components/states";
import { fetchReviewItem } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { isStrictBackendMode } from "@/lib/runtime-mode";
import { useTenantContext } from "@/lib/tenant-context";
import { ReviewActivityTimeline } from "./review-activity-timeline";
import { ReviewDecisionPanel } from "./review-decision-panel";
import { SendReadinessPanel } from "./send-readiness-panel";
import { reviewDtoToItem, type ReviewItem } from "./review-sample-data";

export function ReviewWorkspace({ item, onListRefresh }: { item: ReviewItem; onListRefresh?: () => Promise<void> }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const strictBackendMode = isStrictBackendMode();
  const [activeItem, setActiveItem] = useState<ReviewItem>(item);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [strictError, setStrictError] = useState<string | null>(null);

  const loadReviewItem = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      if (strictBackendMode) {
        setStrictError("Review item detail backend mock API read did not complete in strict backend mode.");
        setLoading(false);
        return;
      }
      setActiveItem(item);
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await fetchReviewItem(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        item.id,
      );
      setActiveItem(reviewDtoToItem(res.review_item, item));
      setUsingFallback(false);
      setStrictError(null);
    } catch (err) {
      if (strictBackendMode) {
        setStrictError("Review item detail backend mock API read failed in strict backend mode.");
      } else {
        console.error("Failed to load review item detail, falling back to read-only local/mock review data:", err);
        setActiveItem(item);
        setUsingFallback(true);
      }
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, item, strictBackendMode]);

  const refreshAfterAction = useCallback(async () => {
    await loadReviewItem();
    await onListRefresh?.();
  }, [loadReviewItem, onListRefresh]);

  useEffect(() => {
    loadReviewItem();
  }, [loadReviewItem]);

  if (strictError) {
    return <ErrorState title="Strict backend mode: review item detail failed" description={strictError} />;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-medium border border-border bg-panel2 p-3 text-caption text-muted">
        {loading
          ? "Loading backend mock review item..."
          : usingFallback
            ? "Backend unavailable or auth missing. Showing read-only local/mock review data fixture fallback."
            : "Review item loaded from backend mock API. Approve, reject, and request-regeneration are local/mock actions; send-gate and outbound sending remain disabled."}
      </div>
      <DraftPreview draft={activeItem.draft} />
      <div className="grid gap-4 xl:grid-cols-2">
        <BentoCard title="Evidence/source list" description="Read-only local/mock evidence for the selected review item. No provider, scraper, or embeddings write is called." badge="Evidence shell">
          <EvidenceList evidence={activeItem.draft.evidence} />
        </BentoCard>
        <BentoCard title="Claim highlights" description="Unsupported claims can request backend mock regeneration, but no live AI/provider generation is called in this slice." badge="Claims">
          <ClaimHighlighter claims={activeItem.draft.unsupportedClaims} />
        </BentoCard>
      </div>
      <GroundednessPanel draft={activeItem.draft} />
      <DraftGatePanel draft={activeItem.draft} />
      <ReviewDecisionPanel item={activeItem} onRefresh={refreshAfterAction} />
      <SendReadinessPanel item={activeItem} />
      <ReviewActivityTimeline item={activeItem} />
    </div>
  );
}
