import { Database } from "lucide-react";

import { Badge } from "@/components/ui/badge";

export function KnowledgeChunkCard({ title, excerpt, source }: { title: string; excerpt: string; source: string }) {
  return (
    <div className="rounded-medium border border-border bg-panel2 p-4">
      <div className="flex items-start gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-small bg-bluebg text-blue">
          <Database className="size-4" />
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-small font-semibold text-text">{title}</p>
            <Badge variant="outline">{source}</Badge>
          </div>
          <p className="mt-2 text-small text-muted">{excerpt}</p>
        </div>
      </div>
    </div>
  );
}
