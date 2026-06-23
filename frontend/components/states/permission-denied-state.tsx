import { ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";

import { StateShell } from "./state-shell";

export function PermissionDeniedState({
  title = "Permission locked",
  description = "Your role is not allowed to view or change this tenant resource. Backend RBAC and object authorization remain the source of truth.",
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
      icon={ShieldAlert}
      tone="locked"
      primaryAction={primaryAction}
      secondaryAction={secondaryAction}
    />
  );
}
