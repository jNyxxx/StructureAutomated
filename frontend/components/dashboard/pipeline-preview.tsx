import { BarChart3, FileText, MailCheck, Send, Sparkles, Upload } from "lucide-react";

import { StatusBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { MetricCard } from "@/components/dashboard/metric-card";

const metrics = [
  { title: "Prospects", value: "Demo", description: "CSV import route exists; data API pending.", icon: Upload },
  { title: "Campaigns", value: "Shell", description: "Campaign API not mounted.", icon: Send },
  { title: "Drafts", value: "Mock", description: "Draft generation remains backend-gated.", icon: Sparkles },
  { title: "Reviews", value: "Pending", description: "Human review shell only.", icon: FileText },
  { title: "Mock sends", value: "Locked", description: "No real sending; mock send pending wiring.", icon: MailCheck, tone: "locked" as const },
  { title: "Outcomes", value: "Preview", description: "Outcomes route shell exists; API pending.", icon: BarChart3 },
];

export function PipelinePreview() {
  return (
    <BentoCard title="Pipeline snapshot" description="Demo-safe placeholders; no product API calls are made." badge="Demo data" className="xl:col-span-2">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((metric) => (
          <MetricCard
            key={metric.title}
            title={metric.title}
            value={metric.value}
            description={metric.description}
            icon={metric.icon}
            tone={metric.tone ?? "default"}
            status="Pending API"
          />
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusBadge status="mock_queued" />
        <StatusBadge status="pending_review" />
        <StatusBadge status="blocked" />
      </div>
    </BentoCard>
  );
}
