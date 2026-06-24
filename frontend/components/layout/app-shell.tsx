"use client";

import type { ReactNode } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { MobileNav } from "@/components/layout/mobile-nav";
import { TopCommandBar } from "@/components/layout/top-command-bar";

import { TenantStatusCard } from "@/lib/tenant-context";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-bg text-text relative overflow-x-hidden">
      <div className="tech-grid-bg" />
      <div className="fixed inset-y-0 left-0 z-40 hidden w-sidebar lg:block">
        <AppSidebar />
      </div>
      <div className="min-h-screen lg:pl-sidebar relative z-10">
        <TopCommandBar mobileNav={<MobileNav />} />
        <main className="space-y-6 p-4 sm:p-6 lg:p-page-desktop">
          <TenantStatusCard />
          {children}
        </main>
      </div>
    </div>
  );
}
