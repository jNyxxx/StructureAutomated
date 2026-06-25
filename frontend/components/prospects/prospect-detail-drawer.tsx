"use client";

import { useCallback, useEffect, useState } from "react";
import { ShieldAlert, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { fetchContact } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import type { Contact } from "@/lib/schemas";
import type { ProspectRow } from "./prospect-sample-data";

export function ProspectDetailDrawer({ prospect }: { prospect: ProspectRow }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const blocked = prospect.suppressionStatus === "suppressed" || prospect.campaignStatus === "blocked";

  const loadContact = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || !prospect.contactId) {
      setContact(null);
      setUsingFallback(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await fetchContact(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        prospect.contactId,
      );
      setContact(res.contact);
      setUsingFallback(false);
    } catch (err) {
      console.error("Failed to load contact detail, falling back to read-only local/mock data:", err);
      setContact(null);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, prospect.contactId]);

  useEffect(() => {
    loadContact();
  }, [loadContact]);

  const displayCompany = contact?.company_name ?? prospect.company;
  const displayTitle = contact?.title ?? prospect.title;
  const displayDomain = contact?.domain ?? prospect.emailDomain;

  return (
    <div className="space-y-4 text-small text-muted">
      <div className="flex items-center gap-2 rounded-medium border border-blue/25 bg-bluebg p-3">
        <ShieldCheck className="size-4 text-blue" /> {loading ? "Loading read-only contact detail..." : usingFallback ? "Read-only local/mock prospect detail fallback." : "Read-only backend mock API contact detail."}
      </div>
      {blocked ? (
        <div className="flex items-center gap-2 rounded-medium border border-red/25 bg-redbg p-3">
          <ShieldAlert className="size-4 text-red" /> Suppression/compliance warning: keep outreach actions blocked.
        </div>
      ) : null}
      <dl className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Company</dt>
          <dd>{displayCompany}</dd>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Role / domain</dt>
          <dd>{displayTitle} / {displayDomain}</dd>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Source</dt>
          <dd>{prospect.source}</dd>
        </div>
        <div className="rounded-medium border border-border bg-panel2 p-3">
          <dt className="font-semibold text-text">Safe notes</dt>
          <dd>{prospect.safeNotes}</dd>
        </div>
      </dl>
      <div className="flex flex-wrap gap-2">
        <GateReasonBadge state="pending" label="Enrich locked" />
        <GateReasonBadge state="blocked" label="No real sending" />
        <GateReasonBadge state="pending" label="Campaign actions locked" />
      </div>
    </div>
  );
}
