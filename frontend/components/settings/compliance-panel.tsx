"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { fetchComplianceProfile } from "@/lib/backend-api";
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

function profileStatus(profile: ComplianceProfile) {
  return [
  { label: `${profile.jurisdiction}-first baseline`, state: "warning" as const, note: "Backend mock API profile only; legal review still required before live sending." },
  { label: "Suppression", state: "passed" as const, note: "Suppression read-side wiring uses backend mock API data with fixture fallback." },
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

  const controls = profileStatus(profile);

  return (
    <BentoCard
      title="Compliance baseline"
      description="Read-only compliance summary from the backend mock API. Live providers, webhooks, and mutations remain disabled."
      badge={loading ? "Loading" : usingFallback ? "Fixture fallback" : "Backend mock API"}
    >
      <div className="mb-4 rounded-medium border border-border bg-panel2 p-3 text-caption text-muted">
        {loading
          ? "Loading read-only compliance profile..."
          : usingFallback
            ? "Backend unavailable or auth missing. Showing read-only local/mock fixture fallback."
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
    </BentoCard>
  );
}
