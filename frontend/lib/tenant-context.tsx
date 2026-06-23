"use client";

import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/api-client";
import { fetchAuthMe } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import type { Principal } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { ErrorState, LoadingState, PermissionDeniedState } from "@/components/states";

export type TenantSessionStatus = "idle" | "loading" | "ready" | "session_unavailable" | "denied" | "error";

export interface TenantContextValue {
  selectedTenantId: string | null;
  confirmedTenantId: string | null;
  isConfirmed: boolean;
  principal: Principal | null;
  role: string | null;
  email: string | null;
  membershipVersion: number | null;
  mfaVerified: boolean | null;
  status: TenantSessionStatus;
  requestId: string | null;
  correlationId: string | null;
  setSelectedTenantId: (tenantId: string | null) => void;
}

const TenantContext = createContext<TenantContextValue | null>(null);

export function TenantProvider({
  children,
  initialTenantId = null,
  confirmedTenantId = null,
}: {
  children: ReactNode;
  initialTenantId?: string | null;
  confirmedTenantId?: string | null;
}) {
  const auth = useFrontendAuth();
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(
    initialTenantId ?? confirmedTenantId,
  );
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [status, setStatus] = useState<TenantSessionStatus>("idle");
  const [requestId, setRequestId] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    if (!auth.isLoaded) {
      setStatus("loading");
      return () => {
        active = false;
      };
    }

    if (!auth.isSignedIn) {
      setPrincipal(null);
      setStatus("session_unavailable");
      return () => {
        active = false;
      };
    }

    setStatus("loading");
    fetchAuthMe({
      getToken: auth.getToken,
      getTenantId: () => selectedTenantId,
    })
      .then((response) => {
        if (!active) return;
        setPrincipal(response.principal);
        setSelectedTenantId((current) => current ?? response.principal.tenant_id);
        setRequestId(null);
        setCorrelationId(null);
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (!active) return;
        setPrincipal(null);
        if (error instanceof ApiError) {
          setRequestId(error.requestId);
          setCorrelationId(error.correlationId);
          setStatus(error.status === 401 || error.status === 403 ? "denied" : "error");
        } else {
          setRequestId(null);
          setCorrelationId(null);
          setStatus("error");
        }
      });

    return () => {
      active = false;
    };
  }, [auth, selectedTenantId]);

  const effectiveConfirmedTenantId = principal?.tenant_id ?? confirmedTenantId;

  const value = useMemo<TenantContextValue>(
    () => ({
      selectedTenantId,
      confirmedTenantId: effectiveConfirmedTenantId,
      isConfirmed: Boolean(selectedTenantId && selectedTenantId === effectiveConfirmedTenantId),
      principal,
      role: principal?.role ?? null,
      email: principal?.email ?? null,
      membershipVersion: principal?.membership_version ?? null,
      mfaVerified: principal?.mfa_verified ?? null,
      status,
      requestId,
      correlationId,
      setSelectedTenantId,
    }),
    [correlationId, effectiveConfirmedTenantId, principal, requestId, selectedTenantId, status],
  );

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenantContext(): TenantContextValue {
  const value = useContext(TenantContext);
  if (!value) {
    throw new Error("TenantProvider is required.");
  }
  return value;
}

export function TenantStatusCard() {
  const tenant = useTenantContext();

  if (tenant.status === "loading") {
    return <LoadingState title="Loading tenant session" description="Checking /auth/me before tenant data is trusted." />;
  }

  if (tenant.status === "session_unavailable") {
    return (
      <PermissionDeniedState
        title="Session unavailable"
        description="The frontend auth shell is not signed in, so /auth/me is not called and tenant data remains locked."
      />
    );
  }

  if (tenant.status === "denied") {
    return (
      <PermissionDeniedState
        title="Tenant access denied"
        description="/auth/me rejected the current session. Tenant data remains read-only/denied until backend auth confirms access."
      />
    );
  }

  if (tenant.status === "error") {
    return (
      <ErrorState
        title="Tenant session unavailable"
        description="/auth/me failed or returned an invalid response. Tenant data remains locked."
        requestId={tenant.requestId}
        correlationId={tenant.correlationId}
      />
    );
  }

  if (!tenant.selectedTenantId) {
    return (
      <PermissionDeniedState
        title="Select a tenant"
        description="Select a tenant before loading protected data. Backend tenant context must confirm access before queries are trusted."
      />
    );
  }

  if (!tenant.isConfirmed) {
    return (
      <PermissionDeniedState
        title="Tenant access not confirmed"
        description="Tenant access is not confirmed by /auth/me yet. Data access remains read-only/denied."
      />
    );
  }

  return (
    <div className="rounded-xl border border-green/30 bg-goodbg p-4 text-small text-muted shadow-panel">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-semibold text-text">Tenant access confirmed</p>
          <p className="mt-1">Tenant {tenant.confirmedTenantId} confirmed by /auth/me.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {tenant.role ? <Badge variant="success">{tenant.role}</Badge> : null}
          {tenant.mfaVerified ? <Badge variant="success">MFA verified</Badge> : <Badge variant="warning">MFA unknown</Badge>}
        </div>
      </div>
    </div>
  );
}
