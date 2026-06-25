"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, Lock, Plus } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { createCampaign } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";

const steps = [
  "Campaign details",
  "Prospect selection",
  "Research/RAG settings",
  "Draft rules",
  "Safety/review gates",
  "Mock send/follow-up settings",
  "Review summary",
];

type ActionState = "idle" | "submitting" | "success" | "error";

export function CampaignBuilderShell() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [state, setState] = useState<ActionState>("idle");
  const [createdCampaign, setCreatedCampaign] = useState<{ id: string; name: string; status: string } | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);
  const canSubmit = auth.isLoaded && auth.isSignedIn && Boolean(selectedTenantId) && state !== "submitting";

  async function handleCreateCampaign() {
    if (!canSubmit || !selectedTenantId) return;

    setState("submitting");
    setCreatedCampaign(null);
    setError(null);

    try {
      const res = await createCampaign(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        {
          name: "CRE Local Mock Campaign",
          description: "Created from the local/mock campaign builder UI using the backend mock API only.",
          goal: "Book qualified owner conversations without real sending.",
          target_segment: "CRE / Local Mock",
          notes: "No live scraping, enrichment, provider calls, drafts, sends, follow-ups, Stripe, SMS, OAuth, or production actions are enabled.",
        },
      );

      if (!res.campaign) {
        setError({ message: "The backend mock API did not return a campaign. No success was recorded.", code: "CAMPAIGN_MISSING", requestId: null });
        setState("error");
        return;
      }

      setCreatedCampaign({ id: res.campaign.id, name: res.campaign.name, status: res.campaign.status });
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock campaign create failed safely. No campaign was created.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  return (
    <div className="space-y-6">
      <BentoCard
        title="Campaign builder shell"
        description="Local/mock campaign builder. Create uses the backend mock API only; research, drafts, sends, follow-ups, and providers remain disabled."
        badge="Backend mock API"
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {steps.map((step, index) => (
            <div key={step} className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-caption text-subtle">
                {index < 2 ? <CheckCircle2 className="size-4 text-green" /> : index < 5 ? <CheckCircle2 className="size-4 text-blue" /> : <Lock className="size-4 text-yellow" />}
                Step {index + 1}
              </div>
              <p className="mt-1 text-small font-semibold text-text">{step}</p>
              <GateReasonBadge state={index < 2 ? "passed" : index < 5 ? "pending" : "blocked"} className="mt-3" />
            </div>
          ))}
        </div>
      </BentoCard>

      <div className="rounded-xl border border-blue/30 bg-bluebg/40 p-5 shadow-panel">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-semibold text-text">Create local/mock campaign</p>
            <p className="mt-2 text-small text-muted">
              This creates a campaign through the backend mock API only. It does not start research, call enrichment providers, scrape websites, generate drafts, send messages, schedule follow-ups, or enable production.
            </p>
          </div>
          <GateReasonBadge state="passed" label="Campaign create mock" />
        </div>

        {state === "success" && createdCampaign ? (
          <div className="mt-4 rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> Backend mock campaign created
            </div>
            <p className="mt-2 text-small text-muted">
              {createdCampaign.name} was returned by the backend mock API with status {createdCampaign.status}.
            </p>
            <Button asChild className="mt-4" variant="secondary">
              <Link href={`/campaigns/${createdCampaign.id}`}>Open created campaign detail</Link>
            </Button>
          </div>
        ) : null}

        {state === "error" && error ? (
          <div className="mt-4 rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> Backend mock campaign create failed safely
            </div>
            <p className="mt-2 text-small text-muted">{error.message}</p>
            <p className="mt-2 text-caption text-muted">
              Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No fake success was recorded.
            </p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={handleCreateCampaign} disabled={!canSubmit}>
            {state === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
            {state === "submitting" ? "Creating via backend mock API" : "Create campaign"}
          </Button>
          <Button variant="secondary" disabled>
            Save draft
          </Button>
          <Button variant="secondary" disabled>
            <Lock className="size-4" /> Start research locked
          </Button>
          <Button variant="secondary" disabled>
            <Lock className="size-4" /> Generate drafts locked
          </Button>
        </div>
      </div>
    </div>
  );
}
