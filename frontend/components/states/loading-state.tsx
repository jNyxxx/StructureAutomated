import { Loader2 } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";

import { StateShell } from "./state-shell";

export function LoadingState({
  title = "Loading",
  description = "Preparing the local/mock MVP view safely.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <StateShell title={title} description={description} icon={Loader2} tone="pending">
      <div className="space-y-3">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-24 w-full" />
      </div>
    </StateShell>
  );
}
