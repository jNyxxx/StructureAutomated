import Link from "next/link";
import { BarChart3, FileText, Lock, MailCheck, Search, Send, Users } from "lucide-react";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { CampaignActivityTimeline } from "./campaign-activity-timeline";
import { CampaignFlowPanel } from "./campaign-flow-panel";
import { CampaignGatesPanel } from "./campaign-gates-panel";
import type { CampaignRow } from "./campaign-sample-data";
import { BentoCard } from "@/components/dashboard/bento-card";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Button } from "@/components/ui/button";

export function CampaignDetail({ campaign }: { campaign: CampaignRow }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Selected prospects" value={String(campaign.selectedProspects)} description="Local/demo count only." icon={Users} status="Demo data" />
        <MetricCard title="Research/RAG" value="Preview" description={campaign.researchProgress} icon={Search} status="Pending API" tone="warning" />
        <MetricCard title="Draft/review" value="Locked" description={campaign.reviewStatus} icon={FileText} status="Pending API" tone="locked" />
        <MetricCard title="Send gate" value="No-send" description="No real sending in this MVP UI." icon={MailCheck} status="Blocked" tone="locked" />
      </div>

      <BentoCard title="Campaign overview" description={campaign.safeSummary} badge="Local/demo">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="text-caption text-subtle">Segment</p>
            <p className="mt-1 text-small font-semibold text-text">{campaign.segment}</p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="text-caption text-subtle">Draft progress</p>
            <p className="mt-1 text-small font-semibold text-text">{campaign.draftProgress}</p>
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <p className="text-caption text-subtle">Follow-up</p>
            <p className="mt-1 text-small font-semibold text-text">{campaign.followUpStatus}</p>
          </div>
        </div>
      </BentoCard>

      <CampaignFlowPanel />

      <div className="grid gap-4 xl:grid-cols-2">
        <CampaignGatesPanel />
        <BentoCard title="Deliverability and outcomes preview" description="Links point to existing frontend shells only; no live analytics APIs are called." badge="Preview">
          <div className="grid gap-3 sm:grid-cols-2">
            <Button asChild variant="secondary">
              <Link href="/deliverability">
                <Send className="size-4" /> Deliverability shell
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/outcomes">
                <BarChart3 className="size-4" /> Outcomes shell
              </Link>
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <StatusBadge status="pending_review" />
            <GateReasonBadge state="blocked" label="Export locked" />
            <GateReasonBadge state="blocked" label="Mock send locked" />
          </div>
        </BentoCard>
      </div>

      <CampaignActivityTimeline />

      <div className="rounded-xl border border-yellow/30 bg-warnbg p-4 text-small text-muted shadow-panel">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-semibold text-text">All campaign mutations are locked</p>
            <p className="mt-1">
              Create campaign, add/remove contacts, start research, generate drafts, approve drafts, mock send, schedule follow-up, and export remain disabled until backend APIs exist.
            </p>
          </div>
          <Button disabled>
            <Lock className="size-4" /> Actions locked
          </Button>
        </div>
      </div>
    </div>
  );
}
