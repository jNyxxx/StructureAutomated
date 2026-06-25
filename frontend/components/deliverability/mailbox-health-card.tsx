import { MailCheck, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { mailboxHealth, type MailboxHealth } from "./deliverability-sample-data";

export function MailboxHealthCard({ mailboxes = mailboxHealth }: { mailboxes?: MailboxHealth[] }) {
  return (
    <BentoCard title="Mailbox health" description="Read-only local/mock or backend mock API mailbox preview. No provider integration, inbox monitoring, DNS write, or real sending." badge="Read-only">
      <div className="space-y-3">
        {mailboxes.map((mailbox) => (
          <div key={mailbox.label} className="rounded-medium border border-border bg-panel2 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex gap-3">
                <div className="flex size-10 items-center justify-center rounded-medium bg-bluebg text-blue">
                  {mailbox.status === "blocked" ? <ShieldAlert className="size-5" /> : <MailCheck className="size-5" />}
                </div>
                <div>
                  <p className="text-small font-semibold text-text">{mailbox.label}</p>
                  <p className="mt-1 text-caption text-muted">{mailbox.note}</p>
                </div>
              </div>
              <GateReasonBadge state={mailbox.status === "blocked" ? "blocked" : mailbox.status === "healthy" ? "passed" : "warning"} label={mailbox.status} />
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <div className="rounded-small border border-border bg-panel p-2">
                <p className="text-caption text-subtle">Mock score/cap</p>
                <p className="text-small font-semibold text-text">{mailbox.dailyLimit}</p>
              </div>
              <div className="rounded-small border border-border bg-panel p-2">
                <p className="text-caption text-subtle">Used today</p>
                <p className="text-small font-semibold text-text">{mailbox.usedToday}</p>
              </div>
              <div className="rounded-small border border-border bg-panel p-2">
                <p className="text-caption text-subtle">Auth checks passed</p>
                <p className="text-small font-semibold text-text">{mailbox.warmupDay}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
