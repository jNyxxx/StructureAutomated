"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchDraft, fetchDraftEvidence } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { DraftGatePanel } from "./draft-gate-panel";
import { DraftPreview } from "./draft-preview";
import { GroundednessPanel } from "./groundedness-panel";
import { draftToRow, evidenceToItem, type DraftRow } from "./draft-sample-data";

export function DraftDetailDrawer({ draft }: { draft: DraftRow }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [activeDraft, setActiveDraft] = useState<DraftRow>(draft);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  const loadDraft = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setActiveDraft(draft);
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const [draftRes, evidenceRes] = await Promise.all([
        fetchDraft(
          {
            getToken: auth.getToken,
            getTenantId: () => selectedTenantId,
          },
          draft.id,
        ),
        fetchDraftEvidence(
          {
            getToken: auth.getToken,
            getTenantId: () => selectedTenantId,
          },
          draft.id,
          { limit: 25 },
        ),
      ]);
      setActiveDraft(draftToRow(draftRes.draft, draft, evidenceRes.evidence.map(evidenceToItem)));
      setUsingFallback(false);
    } catch (err) {
      console.error("Failed to load draft detail/evidence, falling back to read-only local/mock draft data:", err);
      setActiveDraft(draft);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, draft]);

  useEffect(() => {
    loadDraft();
  }, [loadDraft]);

  return (
    <div className="space-y-4">
      <div className="rounded-medium border border-border bg-panel2 p-3 text-caption text-muted">
        {loading
          ? "Loading read-only backend mock draft detail/evidence..."
          : usingFallback
            ? "Backend unavailable or auth missing. Showing read-only local/mock draft data fixture fallback."
            : "Draft detail and evidence loaded from backend mock API. Generate, review, and send actions remain disabled."}
      </div>
      <DraftPreview draft={activeDraft} />
      <GroundednessPanel draft={activeDraft} />
      <DraftGatePanel draft={activeDraft} />
    </div>
  );
}
