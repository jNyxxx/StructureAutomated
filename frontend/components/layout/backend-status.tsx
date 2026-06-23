"use client";

import { Activity, AlertTriangle, CheckCircle2, WifiOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ServerErrorWithRequestId } from "@/components/states";
import { useBackendReadyStatus } from "@/lib/use-backend-status";

function stateVariant(state: string) {
  if (state === "healthy") return "success";
  if (state === "degraded" || state === "unknown") return "warning";
  return "danger";
}

function StateIcon({ state }: { state: string }) {
  if (state === "healthy") return <CheckCircle2 className="size-4" />;
  if (state === "unavailable") return <WifiOff className="size-4" />;
  if (state === "degraded") return <AlertTriangle className="size-4" />;
  return <Activity className="size-4" />;
}

export function BackendStatusBadge() {
  const status = useBackendReadyStatus();

  return (
    <Badge variant={stateVariant(status.state)} className="gap-1.5">
      <StateIcon state={status.state} />
      {status.label}
    </Badge>
  );
}

export function BackendReadinessPanel() {
  const status = useBackendReadyStatus();

  if (status.state === "unavailable") {
    return <ServerErrorWithRequestId requestId={status.requestId} correlationId={status.correlationId} />;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>Local backend readiness</CardTitle>
            <CardDescription>{status.message}</CardDescription>
          </div>
          <BackendStatusBadge />
        </div>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3 text-small text-muted sm:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <dt className="font-semibold text-text">Endpoint</dt>
            <dd>/ready</dd>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <dt className="font-semibold text-text">Raw status</dt>
            <dd>{status.rawStatus ?? "unknown"}</dd>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <dt className="font-semibold text-text">Production approval</dt>
            <dd>Not approved</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
