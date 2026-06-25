"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, MousePointer2 } from "lucide-react";

import { CampaignDetail } from "@/components/campaigns/campaign-detail";
import { campaignToRow, getCampaignById, type CampaignRow } from "@/components/campaigns/campaign-sample-data";
import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { ErrorState, LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api-client";
import { fetchCampaign, fetchProspects, selectCampaignContact, updateCampaign } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { isStrictBackendMode } from "@/lib/runtime-mode";
import { useTenantContext } from "@/lib/tenant-context";

type ActionState = "idle" | "submitting" | "success" | "error";

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const strictBackendMode = isStrictBackendMode();
  const fallbackCampaign = getCampaignById(params.id);
  const [campaign, setCampaign] = useState<CampaignRow | undefined>(fallbackCampaign);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(Boolean(fallbackCampaign));
  const [contactId, setContactId] = useState<string | null>(null);
  const [contactLabel, setContactLabel] = useState("backend mock contact");
  const [updateState, setUpdateState] = useState<ActionState>("idle");
  const [selectState, setSelectState] = useState<ActionState>("idle");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);
  const [strictError, setStrictError] = useState<string | null>(null);

  const loadCampaign = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      if (strictBackendMode) {
        setStrictError("Campaign detail requires backend mock API reads in strict backend mode.");
        setLoading(false);
        return;
      }
      setCampaign(fallbackCampaign);
      setUsingFallback(Boolean(fallbackCampaign));
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await fetchCampaign(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        params.id,
      );
      setCampaign(campaignToRow(res.campaign));
      setUsingFallback(false);
      setStrictError(null);
    } catch (err) {
      if (strictBackendMode) {
        setStrictError("NETWORK_ERROR: Campaign detail backend mock API read failed in strict backend mode.");
      } else {
        console.error("Failed to load campaign detail, falling back to read-only local/mock data:", err);
        setCampaign(fallbackCampaign);
        setUsingFallback(Boolean(fallbackCampaign));
      }
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId, params.id, fallbackCampaign, strictBackendMode]);

  const loadSelectableContact = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) return;

    try {
      const res = await fetchProspects(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        { limit: 1 },
      );
      const first = res.prospects[0];
      if (first) {
        setContactId(first.contact_id);
        setContactLabel(first.full_name ?? first.company_name ?? "backend mock contact");
      }
    } catch (err) {
      console.error("Failed to load selectable backend mock contact:", err);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadCampaign();
  }, [loadCampaign]);

  useEffect(() => {
    loadSelectableContact();
  }, [loadSelectableContact]);

  async function handleUpdateCampaign() {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || updateState === "submitting") return;

    setUpdateState("submitting");
    setSelectState("idle");
    setActionMessage(null);
    setActionError(null);

    try {
      const res = await updateCampaign(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        params.id,
        {
          notes: "Updated by the local/mock campaign detail UI through the backend mock API only.",
          status: "review",
        },
      );
      if (!res.campaign) {
        setActionError({ message: "The backend mock API did not return an updated campaign. No success was recorded.", code: "CAMPAIGN_UPDATE_MISSING", requestId: null });
        setUpdateState("error");
        return;
      }
      setCampaign(campaignToRow(res.campaign));
      setUsingFallback(false);
      setActionMessage(`Backend mock campaign update succeeded for ${res.campaign.name}.`);
      setUpdateState("success");
      await loadCampaign();
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setActionError({ message: "The local/mock campaign update failed safely. No fake success was recorded.", code: "UNKNOWN", requestId: null });
      }
      setUpdateState("error");
    }
  }

  async function handleSelectContact() {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || !contactId || selectState === "submitting") return;

    setSelectState("submitting");
    setUpdateState("idle");
    setActionMessage(null);
    setActionError(null);

    try {
      const res = await selectCampaignContact(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        params.id,
        {
          contact_id: contactId,
          status: "selected",
        },
      );
      if (!res.campaign_contact) {
        setActionError({ message: "The backend mock API did not return a campaign contact. No success was recorded.", code: "CAMPAIGN_CONTACT_MISSING", requestId: null });
        setSelectState("error");
        return;
      }
      setActionMessage(`Backend mock contact selection succeeded for ${contactLabel}.`);
      setSelectState("success");
      await loadCampaign();
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setActionError({ message: "The local/mock contact selection failed safely. No fake success was recorded.", code: "UNKNOWN", requestId: null });
      }
      setSelectState("error");
    }
  }

  if (strictError) {
    return <ErrorState title="Strict backend mode: campaign detail failed" description={strictError} />;
  }

  if (!campaign) {
    return <ErrorState title="Campaign row not found" description="Only backend mock API campaigns or local/mock fixture campaign IDs are available in this frontend slice." />;
  }

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Campaign detail"
        title={campaign.name}
        description="Campaign detail from the backend mock API or fixture fallback. Update and contact selection are local/mock only; provider, sending, schedule, export, research, and draft actions remain disabled."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            <Badge variant={usingFallback ? "locked" : "default"}>{loading ? "Loading" : usingFallback ? "Fixture fallback" : "Backend mock API"}</Badge>
            <Button asChild variant="secondary">
              <Link href="/campaigns">
                <ArrowLeft className="size-4" /> Back to campaigns
              </Link>
            </Button>
          </>
        }
      />

      <LocalMockNotice />

      <Card className="border-blue/25 bg-bluebg/50">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-medium bg-bluebg text-blue">
              <MousePointer2 className="size-5" />
            </div>
            <div>
              <CardTitle>Safe local/mock campaign actions</CardTitle>
              <CardDescription>
                Update campaign and select a contact can call backend mock APIs. Start research, generate drafts, approve drafts, send, follow-up, export, enrichment, scraping, and provider actions remain disabled.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <GateReasonBadge state="passed" label="Campaign update mock" />
            <GateReasonBadge state="passed" label="Contact selection mock" />
            <GateReasonBadge state="blocked" label="No real sending" />
            <GateReasonBadge state="blocked" label="No live scraping" />
            <GateReasonBadge state="blocked" label="No provider calls" />
          </div>

          {actionMessage ? (
            <div className="rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
              <div className="flex items-center gap-2 text-small font-semibold text-text">
                <CheckCircle2 className="size-4 text-green" /> {actionMessage}
              </div>
              <p className="mt-2 text-caption text-muted">Campaign detail was refreshed from the backend mock read surface when available.</p>
            </div>
          ) : null}

          {actionError ? (
            <div className="rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
              <div className="flex items-center gap-2 text-small font-semibold text-text">
                <AlertCircle className="size-4 text-red" /> Backend mock campaign action failed safely
              </div>
              <p className="mt-2 text-small text-muted">{actionError.message}</p>
              <p className="mt-2 text-caption text-muted">
                Code: {actionError.code}{actionError.requestId ? ` · Request ID: ${actionError.requestId}` : ""}. No fake success was recorded.
              </p>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button onClick={handleUpdateCampaign} disabled={!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || updateState === "submitting"}>
              {updateState === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
              {updateState === "submitting" ? "Updating via backend mock API" : "Update campaign"}
            </Button>
            <Button onClick={handleSelectContact} disabled={!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || !contactId || selectState === "submitting"} variant="secondary">
              {selectState === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <MousePointer2 className="size-4" />}
              {selectState === "submitting" ? "Selecting contact via backend mock API" : `Select contact${contactId ? `: ${contactLabel}` : ""}`}
            </Button>
            <Button disabled variant="secondary">Start research locked</Button>
            <Button disabled variant="secondary">Generate drafts locked</Button>
            <Button disabled variant="secondary">Mock send locked</Button>
          </div>
        </CardContent>
      </Card>

      <CampaignDetail campaign={campaign} />
    </section>
  );
}
