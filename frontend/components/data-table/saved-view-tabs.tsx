import { Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SavedViewTab } from "./types";

export function SavedViewTabs({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: SavedViewTab[];
  activeTab: string;
  onChange: (tabId: string) => void;
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Saved views">
      {tabs.map((tab) => {
        const active = tab.id === activeTab;
        return (
          <Button
            key={tab.id}
            type="button"
            variant={active ? "default" : "secondary"}
            size="sm"
            role="tab"
            aria-selected={active}
            disabled={tab.locked}
            onClick={() => onChange(tab.id)}
            className={cn("shrink-0 gap-2", tab.locked && "cursor-not-allowed")}
          >
            {tab.locked ? <Lock className="size-3.5" /> : null}
            {tab.label}
            {typeof tab.count === "number" ? <Badge variant="outline">{tab.count}</Badge> : null}
          </Button>
        );
      })}
    </div>
  );
}
