"use client";

import { createContext, type ReactNode, useContext, useMemo, useState } from "react";

export interface TenantContextValue {
  selectedTenantId: string | null;
  confirmedTenantId: string | null;
  isConfirmed: boolean;
  setSelectedTenantId: (tenantId: string) => void;
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
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(
    initialTenantId ?? confirmedTenantId,
  );

  const value = useMemo<TenantContextValue>(
    () => ({
      selectedTenantId,
      confirmedTenantId,
      isConfirmed: Boolean(selectedTenantId && selectedTenantId === confirmedTenantId),
      setSelectedTenantId,
    }),
    [confirmedTenantId, selectedTenantId],
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

  if (!tenant.selectedTenantId) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
        Select a tenant before loading protected data.
      </div>
    );
  }

  if (!tenant.isConfirmed) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Tenant access is not confirmed by the backend yet. Data access remains read-only/denied.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
      Tenant access confirmed for {tenant.confirmedTenantId}.
    </div>
  );
}
