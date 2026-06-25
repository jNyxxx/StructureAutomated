"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { fetchComplianceProfile, updateComplianceProfile } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import type { ComplianceProfile } from "@/lib/schemas";

const fallbackProfile: ComplianceProfile = {
  jurisdiction: "US",
  sending_review_required: true,
  live_sending_allowed: false,
  sms_allowed: false,
  mock_only: true,
};

type ActionState = "idle" | "submitting" | "success" | "error";

function profileStatus(profile: ComplianceProfile) {
  return [
    { label: `${profile.jurisdiction}-first baseline`, state: "warning" as const, note: "Backend mock API profile only; legal review still required before live sending." },
    { label: "Suppression", state: "passed" as const, note: "Suppression read/write wiring uses backend mock API data with fixture fallback." },
    { label: "Unsubscribe", state: "pending" as const, note: "Real unsubscribe webhooks and provider sync remain deferred." },
    {
      label: "Manual approval",
      state: profile.sending_review_required ? "warning" as const : "blocked" as const,
      note: profile.sending_review_required
        ? "Human review remains required and never bypasses safety or send gates."
        : "Backend mock API says review is not required, but live sending remains locked.",
    },
    {
      label: "Live email sending",
      state: profile.live_sending_allowed ? "warning" as const : "blocked" as const,
      note: profile.live_sending_allowed
        ? "Backend mock API flag only. This UI still does not enable real sending."
        : "Real sending is disabled in local/mock MVP.",
    },
    {
      label: "SMS sending",
      state: profile.sms_allowed ? "warning" as const : "blocked" as const,
      note: profile.sms_allowed
        ? "Backend mock API flag only. Real SMS remains deferred."
        : "Real SMS remains deferred.",
    },
  ];
}

export function CompliancePanel() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [profile, setProfile] = useState<ComplianceProfile>(fallbackProfile);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [state, setState] = useState<ActionState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);

  const loadProfile = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setProfile(fallbackProfile);
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await fetchComplianceProfile({
        getToken: auth.getToken,
        getTenantId: () => selectedTenantId,
      });
      setProfile(res.compliance_profile);
      setUsingFallback(false);
    } catch (err) {
      console.error("Failed to load compliance profile, falling back to read-only local/mock data:", err);
      setProfile(fallbackProfile);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  async function handleUpdateComplianceProfile() {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || state === "submitting") return;

    setState("submitting");
    setMessage(null);
    setError(null);

    try {
      const res = await updateComplianceProfile(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        {
          jurisdiction: "US",
          sending_review_required: true,
          live_sending_allowed: false,
          sms_allowed: false,
        },
      );
      setProfile(res.compliance_profile);
      setUsingFallback(false);
      setMessage(`Backend mock compliance profile update succeeded for ${res.compliance_profile.jurisdiction}. Relevant read surface refreshed from the backend mock response.`);
      setState("success");
      await loadProfile();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock compliance profile update failed safely. No provider sync or production compliance automation was triggered.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  const controls = profileStatus(profile);

  return (
    <BentoCard
      title="Compliance baseline"
      description="Compliance summary from the backend mock API. The update action is local/mock only; live providers, webhooks, real sending, and production compliance automation remain disabled."
      badge={loading ? "Loading" : usingFallback ? "Fixture fallback" : "Backend mock API"}
    >
      <div className="mb-4 rounded-medium border border-border bg-panel2 p-3 text-caption text-muted">
        {loading
          ? "Loading compliance profile..."
          : usingFallback
            ? "Backend unavailable or auth missing. Showing local/mock fixture fallback."
            : "Compliance profile loaded from backend mock API. This is not production compliance automation."}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {controls.map((control) => (
          <div key={control.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-9 items-center justify-center rounded-small bg-bluebg text-blue">
                  {control.state === "blocked" ? <ShieldAlert className="size-4" /> : <CheckCircle2 className="size-4" />}
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{control.label}</p>
                  <p className="text-caption text-muted">{control.note}</p>
                </div>
              </div>
              <GateReasonBadge state={control.state} />
            </div>
          </div>
        ))}
      </div>

      {message ? (
        <div className="mt-4 rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <CheckCircle2 className="size-4 text-green" /> {message}
          </div>
          <p className="mt-2 text-caption text-muted">No provider sync, real webhook, live sending, SMS, or production compliance automation was triggered.</p>
        </div>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
          <div className="flex items-center gap-2 text-small font-semibold text-text">
            <AlertCircle className="size-4 text-red" /> Backend mock compliance profile update failed safely
          </div>
          <p className="mt-2 text-small text-muted">{error.message}</p>
          <p className="mt-2 text-caption text-muted">
            Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No fake success was recorded.
          </p>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={handleUpdateComplianceProfile} disabled={!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || state === "submitting"}>
          {state === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
          {state === "submitting" ? "Updating via backend mock API" : "Update local/mock compliance profile"}
        </Button>
        <Button disabled variant="locked">
          Provider sync locked
        </Button>
      </div>
    </BentoCard>
  );
}
