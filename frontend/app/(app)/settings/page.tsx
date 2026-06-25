"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, Building2, CheckCircle2, Loader2, Lock, PlugZap, ShieldCheck, Users, Globe } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { fetchTenantSettings, updateTenantSettings } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import type { Tenant } from "@/lib/schemas";

const links = [
  { href: "/settings/team", label: "Team and roles", icon: Users, note: "RBAC/MFA wired" },
  { href: "/settings/integrations", label: "Integrations", icon: PlugZap, note: "Provider cards locked" },
  { href: "/settings/security", label: "Security", icon: ShieldCheck, note: "Auth/session shell" },
  { href: "/settings/compliance", label: "Compliance", icon: ShieldCheck, note: "Backend mock update" },
  { href: "/settings/suppression", label: "Suppression", icon: Lock, note: "Backend mock actions" },
];

type ActionState = "idle" | "submitting" | "success" | "error";

export default function SettingsPage() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [state, setState] = useState<ActionState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);

  const loadTenant = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetchTenantSettings({
        getToken: auth.getToken,
        getTenantId: () => selectedTenantId,
      });
      setTenant(res.tenant);
    } catch (err) {
      console.error("Failed to fetch tenant settings:", err);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadTenant();
  }, [loadTenant]);

  async function handleUpdateTenantSettings() {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || state === "submitting") return;

    setState("submitting");
    setMessage(null);
    setError(null);

    try {
      const res = await updateTenantSettings(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        {
          name: "Automated Structure Mock Tenant Updated",
          settings: {
            timezone: "Asia/Manila",
            locale: "en-PH",
            mock_settings_update: true,
          },
        },
      );
      setTenant(res.tenant);
      setMessage(`Backend mock tenant settings update succeeded for ${res.tenant.name}. Relevant read surface refreshed from the backend mock response.`);
      setState("success");
      await loadTenant();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock tenant settings update failed safely. No provider sync was triggered.", code: "UNKNOWN", requestId: null });
      }
      setState("error");
    }
  }

  const tenantName = tenant?.name ?? "Automated Structure Demo Tenant";
  const timezone = (tenant?.settings?.timezone as string) ?? "Asia/Manila";
  const locale = (tenant?.settings?.locale as string) ?? "en-PH";

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Tenant settings"
        title="Settings"
        description="Tenant profile settings and wiring status. Tenant update uses the backend mock API only; provider sync, member changes, billing, webhooks, and production actions remain disabled."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
          </>
        }
      />
      <LocalMockNotice />
      <BentoCard
        title="Tenant profile settings"
        description="Tenant settings preview fetched from backend. Save is a local/mock settings update only and does not sync providers."
        badge="Backend mock API"
      >
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Building2 className="size-4 text-blue" /> Tenant
            </div>
            <p className="mt-2 text-small text-muted">{loading ? "Loading..." : tenantName}</p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Globe className="size-4 text-blue" /> Localization
            </div>
            <p className="mt-2 text-small text-muted">
              {loading ? "Loading..." : `Timezone: ${timezone} / Locale: ${locale}`}
            </p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="text-small font-semibold text-text">Save status</p>
            {loading ? (
              <GateReasonBadge state="pending" label="Loading..." className="mt-2" />
            ) : (
              <GateReasonBadge state="passed" label="Settings mock update" className="mt-2" />
            )}
          </div>
        </div>

        {message ? (
          <div className="mt-4 rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> {message}
            </div>
            <p className="mt-2 text-caption text-muted">No provider sync, billing change, member update, webhook, or production action was triggered.</p>
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> Backend mock tenant settings update failed safely
            </div>
            <p className="mt-2 text-small text-muted">{error.message}</p>
            <p className="mt-2 text-caption text-muted">
              Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No fake success was recorded.
            </p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={handleUpdateTenantSettings} disabled={!auth.isLoaded || !auth.isSignedIn || !selectedTenantId || state === "submitting"}>
            {state === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
            {state === "submitting" ? "Saving via backend mock API" : "Save local/mock tenant settings"}
          </Button>
          <Button disabled variant="locked">
            <Lock className="size-4" /> Provider sync locked
          </Button>
        </div>
      </BentoCard>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {links.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-xl border border-border bg-panel p-5 shadow-panel transition hover:border-blue/50"
            >
              <div className="flex items-start gap-3">
                <div className="flex size-10 items-center justify-center rounded-medium bg-bluebg text-blue">
                  <Icon className="size-5" />
                </div>
                <div>
                  <p className="font-semibold text-text">{item.label}</p>
                  <p className="mt-1 text-small text-muted">{item.note}</p>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
