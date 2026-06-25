import type { DeliverabilitySummary, MailboxHealthDto } from "@/lib/schemas";

export interface MailboxHealth {
  label: string;
  status: "healthy" | "warming" | "blocked";
  dailyLimit: number;
  usedToday: number;
  warmupDay: number;
  note: string;
}

export interface DeliverabilityTrendPoint {
  label: string;
  mockSent: number;
  blocked: number;
  suppressed: number;
}

export interface DeliverabilitySummaryView {
  mockSends: number;
  blocked: number;
  duplicates: number;
  suppressed: number;
  safetyDenied: number;
  followUpsScheduled: number;
  followUpsSent: number;
  followUpsSkipped: number;
  throttled: number;
  mockBounced: number;
  mockComplained: number;
  mockOpened: number;
  mockReplied: number;
}

export const mailboxHealth: MailboxHealth[] = [
  {
    label: "owner-demo@example.com",
    status: "warming",
    dailyLimit: 25,
    usedToday: 8,
    warmupDay: 4,
    note: "Read-only local/mock mailbox only. No provider connection.",
  },
  {
    label: "team-demo@example.com",
    status: "blocked",
    dailyLimit: 0,
    usedToday: 0,
    warmupDay: 0,
    note: "Blocked because production sending is not approved.",
  },
];

export const deliverabilitySummary: DeliverabilitySummaryView = {
  mockSends: 18,
  blocked: 11,
  duplicates: 4,
  suppressed: 3,
  safetyDenied: 4,
  followUpsScheduled: 6,
  followUpsSent: 0,
  followUpsSkipped: 5,
  throttled: 2,
  mockBounced: 1,
  mockComplained: 0,
  mockOpened: 7,
  mockReplied: 2,
};

export const domainAuthStatuses = [
  { label: "SPF", status: "demo read-only", state: "pending" as const },
  { label: "DKIM", status: "demo read-only", state: "pending" as const },
  { label: "DMARC", status: "demo read-only", state: "pending" as const },
];

export const warmupSteps = [
  { label: "Day 1", detail: "Mailbox added to local/mock warmup shell", state: "passed" as const },
  { label: "Day 4", detail: "Throttle preview capped at 25/day", state: "warning" as const },
  { label: "Production", detail: "Real provider sending remains blocked", state: "blocked" as const },
];

export const deliverabilityTrend: DeliverabilityTrendPoint[] = [
  { label: "Mon", mockSent: 3, blocked: 4, suppressed: 1 },
  { label: "Tue", mockSent: 4, blocked: 3, suppressed: 1 },
  { label: "Wed", mockSent: 5, blocked: 2, suppressed: 2 },
  { label: "Thu", mockSent: 6, blocked: 2, suppressed: 1 },
];

export const sendGateHealth = [
  { label: "Suppression", state: "warning" as const, note: "Suppressed contacts remain blocked." },
  { label: "Groundedness", state: "warning" as const, note: "Unsupported claims need regeneration." },
  { label: "Billing/access", state: "blocked" as const, note: "Central backend gate required." },
  { label: "Provider send", state: "blocked" as const, note: "No real sending or provider calls." },
];

export function deliverabilityToView(summary: DeliverabilitySummary): DeliverabilitySummaryView {
  return {
    mockSends: summary.sent,
    blocked: summary.blocked,
    duplicates: summary.duplicate_denied,
    suppressed: summary.suppressed,
    safetyDenied: summary.safety_denied,
    followUpsScheduled: summary.followup_sent + summary.followup_skipped,
    followUpsSent: summary.followup_sent,
    followUpsSkipped: summary.followup_skipped,
    throttled: summary.throttled,
    mockBounced: summary.mock_bounced,
    mockComplained: summary.mock_complained,
    mockOpened: summary.mock_opened,
    mockReplied: summary.mock_replied,
  };
}

export function mailboxDtoToHealth(mailbox: MailboxHealthDto): MailboxHealth[] {
  const validCount = [mailbox.spf_valid, mailbox.dkim_valid, mailbox.dmarc_valid].filter(Boolean).length;
  const status: MailboxHealth["status"] = mailbox.reputation_score <= 0 ? "blocked" : validCount === 3 ? "healthy" : "warming";
  return [
    {
      label: mailbox.mock_domain,
      status,
      dailyLimit: mailbox.reputation_score,
      usedToday: 0,
      warmupDay: validCount,
      note: "Read-only backend mock API mailbox/domain health. No real DNS, inbox monitoring, provider sync, or sending call is made.",
    },
  ];
}

export function deliverabilityToTrend(summary: DeliverabilitySummaryView): DeliverabilityTrendPoint[] {
  return [
    { label: "Sent", mockSent: summary.mockSends, blocked: 0, suppressed: 0 },
    { label: "Blocked", mockSent: 0, blocked: summary.blocked, suppressed: 0 },
    { label: "Suppressed", mockSent: 0, blocked: 0, suppressed: summary.suppressed },
    { label: "Safety", mockSent: 0, blocked: summary.safetyDenied + summary.throttled, suppressed: 0 },
  ];
}
