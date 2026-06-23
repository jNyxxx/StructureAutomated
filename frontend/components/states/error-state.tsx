import { AlertTriangle } from "lucide-react";
import type { ReactNode } from "react";

import { StateShell } from "./state-shell";

export function ErrorState({
  title = "Something went wrong",
  description = "The view failed safely without exposing sensitive details.",
  requestId,
  correlationId,
  primaryAction,
  secondaryAction,
}: {
  title?: string;
  description?: string;
  requestId?: string | null;
  correlationId?: string | null;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
}) {
  return (
    <StateShell
      title={title}
      description={description}
      icon={AlertTriangle}
      tone="danger"
      primaryAction={primaryAction}
      secondaryAction={secondaryAction}
    >
      {requestId || correlationId ? (
        <dl className="grid gap-2 rounded-medium border border-border bg-panel2 p-3 text-small text-muted sm:grid-cols-2">
          {requestId ? (
            <div>
              <dt className="font-semibold text-text">Request ID</dt>
              <dd className="break-all">{requestId}</dd>
            </div>
          ) : null}
          {correlationId ? (
            <div>
              <dt className="font-semibold text-text">Correlation ID</dt>
              <dd className="break-all">{correlationId}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
    </StateShell>
  );
}
