import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

import { StateShell } from "./state-shell";

export function EmptyState({
  title = "Nothing here yet",
  description = "Data will appear here after the matching backend flow is available and populated.",
  primaryAction,
  secondaryAction,
}: {
  title?: string;
  description?: string;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
}) {
  return (
    <StateShell
      title={title}
      description={description}
      icon={Inbox}
      tone="default"
      primaryAction={primaryAction}
      secondaryAction={secondaryAction}
    />
  );
}
