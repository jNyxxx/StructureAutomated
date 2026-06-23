import { Activity, Database, Server, ShieldAlert } from "lucide-react";

import { BackendReadinessPanel } from "@/components/layout/backend-status";
import { BentoCard } from "@/components/dashboard/bento-card";
import { GateReasonBadge } from "@/components/badges";

const mountedRoutes = ["GET /health", "GET /live", "GET /ready", "POST /auth/session", "GET /auth/me", "POST /auth/logout", "POST /auth/logout-all"];

export function ReadinessPanel() {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <BackendReadinessPanel />
      <BentoCard title="MVP readiness boundary" description="Frontend may display status, but backend remains authority." badge="Local only">
        <div className="space-y-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <Server className="size-4 text-blue" /> Mounted API status
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {mountedRoutes.map((route) => (
                <span key={route} className="rounded-pill border border-border bg-panel px-2.5 py-1 text-caption text-muted">
                  {route}
                </span>
              ))}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-small font-semibold text-text">
                <Database className="size-4 text-yellow" /> Live DB smoke
              </div>
              <GateReasonBadge state="pending" label="Deferred" className="mt-3" />
            </div>
            <div className="rounded-medium border border-border bg-panel2 p-3">
              <div className="flex items-center gap-2 text-small font-semibold text-text">
                <ShieldAlert className="size-4 text-red" /> Production
              </div>
              <GateReasonBadge state="blocked" label="Not approved" className="mt-3" />
            </div>
          </div>
          <p className="text-caption text-muted">
            Phase 1 backend local/mock evidence is complete through P1-13, but this dashboard must not claim production readiness.
          </p>
          <div className="flex items-center gap-2 text-caption text-subtle">
            <Activity className="size-3.5" /> Health/ready only uses mounted FE-4 routes.
          </div>
        </div>
      </BentoCard>
    </div>
  );
}
