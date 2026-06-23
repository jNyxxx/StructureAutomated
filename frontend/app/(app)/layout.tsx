"use client";

import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { AuthGate } from "@/lib/clerk";
import { TenantProvider } from "@/lib/tenant-context";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <TenantProvider>
        <AppShell>{children}</AppShell>
      </TenantProvider>
    </AuthGate>
  );
}
