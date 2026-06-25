"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, Lock, Pencil, RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { approveReviewItem, rejectReviewItem, requestReviewRegeneration } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { type ReviewItem } from "./review-sample-data";

type ActionState = "idle" | "submitting" | "success" | "error";
type ReviewActionName = "approve" | "reject" | "request-regeneration";

export function ReviewDecisionPanel({ item, onRefresh }: { item: ReviewItem; onRefresh?: () => Promise<void> }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [state, setState] = useState<ActionState>("idle");
  const [activeAction, setActiveAction] = useState<ReviewActionName | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);
  const canAct = auth.isLoaded && auth.isSignedIn && Boolean(selectedTenantId) && state !== "submitting";
  const blockers = [
    { label: "Prompt injection", state: item.draft.promptInjectionGate },
    { label: "Source trust", state: item.draft.sourceTrustGate },
    { label: "Groundedness", state: item.draft.groundednessGate },
    { label: "Unsupported claims", state: item.draft.unsupportedClaims.length === 0 ? "passed" : "blocked" },
    { label: "Suppression", state: item.suppressionStatus === "clear" ? "passed" : "blocked" },
    { label: "Billing/access", state: item.billingAccessLocked ? "blocked" : "passed" },
    { label: "Review action API", state: "passed" },
    { label: "Send gate", state: "blocked" },
  ] as const;

  async function runAction(action: ReviewActionName) {
    if (!canAct || !selectedTenantId) return;

    setState("submitting");
    setActiveAction(action);
    setMessage(null);
    setError(null);

    try {
      const options = {
        getToken: auth.getToken,
        getTenantId: () => selectedTenantId,
      };
      const body = { reason: `Local/mock review action: ${action}. No live AI/provider/send action was called.` };
      const res =
        action === "approve"
          ? await approveReviewItem(options, item.id, body)
          : action === "reject"
            ? await rejectReviewItem(options, item.id, body)
            : await requestReviewRegeneration(options, item.id, body);

      if (!res.review_item) {
        setError({ message: "The backend mock API did not return a review item. No success was recorded.", code: "REVIEW_ACTION_MISSING", requestId: null });
        setState("error");
        return;
      }

      await onRefresh?.();
      setMessage(`Backend mock review action succeeded: ${res.review_item.status}. Review detail/list refresh was requested from backend mock APIs when available.`);
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock review action failed safely. No fake success was recorded.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  return (
    <BentoCard title="Review decision" description="Approve, reject, and request-regeneration call backend mock APIs only. Human approval never bypasses safety, groundedness, suppression, billing, throttles, deliverability, or send gates." badge="Backend mock API">
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          {blockers.map((blocker) => (
            <div key={blocker.label} className="flex items-center justify-between gap-3 rounded-medium border border-border bg-panel2 p-3">
              <p className="text-small font-semibold text-text">{blocker.label}</p>
              <GateReasonBadge state={blocker.state} />
            </div>
          ))}
        </div>

        {state === "success" && message ? (
          <div className="rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> {message}
            </div>
          </div>
        ) : null}

        {state === "error" && error ? (
          <div className="rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> Backend mock review action failed safely
            </div>
            <p className="mt-2 text-small text-muted">{error.message}</p>
            <p className="mt-2 text-caption text-muted">
              Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No fake success was recorded.
            </p>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2 pt-2">
          <Button onClick={() => runAction("approve")} disabled={!canAct}>
            {state === "submitting" && activeAction === "approve" ? <Loader2 className="size-4 animate-spin" /> : <ThumbsUp className="size-4" />}
            {state === "submitting" && activeAction === "approve" ? "Approving via backend mock API" : "Approve review"}
          </Button>
          <Button onClick={() => runAction("reject")} disabled={!canAct} variant="secondary">
            {state === "submitting" && activeAction === "reject" ? <Loader2 className="size-4 animate-spin" /> : <ThumbsDown className="size-4" />}
            {state === "submitting" && activeAction === "reject" ? "Rejecting via backend mock API" : "Reject review"}
          </Button>
          <Button onClick={() => runAction("request-regeneration")} disabled={!canAct} variant="secondary">
            {state === "submitting" && activeAction === "request-regeneration" ? <Loader2 className="size-4 animate-spin" /> : <RotateCcw className="size-4" />}
            {state === "submitting" && activeAction === "request-regeneration" ? "Requesting regeneration via backend mock API" : "Request regeneration"}
          </Button>
          <Button disabled variant="secondary">
            <Pencil className="size-4" /> Edit draft locked
          </Button>
          <Button disabled variant="locked">
            <Lock className="size-4" /> Send-gate/send locked
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
