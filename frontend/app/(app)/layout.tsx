"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { BillingBanner } from "@/components/billing-banner";
import { AuthGate } from "@/lib/clerk";
import { TenantProvider, TenantStatusCard } from "@/lib/tenant-context";

const nav = [
  ["Dashboard", "/dashboard"],
  ["Billing", "/billing"],
  ["Audit logs", "/audit-logs"],
  ["Settings", "/settings"],
] as const;

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <TenantProvider>
        <div className="min-h-screen bg-slate-50">
          <header className="border-b bg-white px-8 py-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  AutomatedStructure
                </p>
                <h1 className="text-2xl font-semibold">Secure tenant console</h1>
              </div>
              <nav className="flex flex-wrap gap-3 text-sm">
                {nav.map(([label, href]) => (
                  <Link className="rounded-md border bg-white px-3 py-2 hover:bg-slate-50" href={href} key={href}>
                    {label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main className="space-y-6 p-8">
            <TenantStatusCard />
            <BillingBanner />
            {children}
          </main>
        </div>
      </TenantProvider>
    </AuthGate>
  );
}
