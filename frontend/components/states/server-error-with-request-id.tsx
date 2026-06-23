import { Button } from "@/components/ui/button";

import { ErrorState } from "./error-state";

export function ServerErrorWithRequestId({
  requestId,
  correlationId,
}: {
  requestId?: string | null;
  correlationId?: string | null;
}) {
  return (
    <ErrorState
      title="Server request failed"
      description="The backend returned an error envelope. Share the request ID when debugging; raw server details are not shown in the UI."
      requestId={requestId}
      correlationId={correlationId}
      secondaryAction={<Button variant="secondary">Copy request ID</Button>}
    />
  );
}
