import { Archive, Trash2 } from "lucide-react";

import { BentoCard } from "@/components/dashboard/bento-card";
import { retentionItems } from "./privacy-sample-data";

export function DataRetentionPanel() {
  return (
    <BentoCard title="Data retention" description="Soft delete → hard delete after 30 days, with suppression minimums preserved where needed." badge="30-day policy">
      <div className="space-y-3">
        {retentionItems.map((item, index) => (
          <div key={item.label} className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex gap-3">
              <div className="flex size-9 items-center justify-center rounded-small bg-violetbg text-violet">
                {index === 0 ? <Trash2 className="size-4" /> : <Archive className="size-4" />}
              </div>
              <div>
                <p className="text-small font-semibold text-text">{item.label}</p>
                <p className="text-caption text-muted">{item.detail}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
