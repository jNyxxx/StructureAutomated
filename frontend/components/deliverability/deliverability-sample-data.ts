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

export const mailboxHealth: MailboxHealth[] = [
  {
    label: "owner-demo@example.com",
    status: "warming",
    dailyLimit: 25,
    usedToday: 8,
    warmupDay: 4,
    note: "Local/demo mailbox only. No provider connection.",
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

export const deliverabilitySummary = {
  mockSends: 18,
  blocked: 11,
  duplicates: 4,
  suppressed: 3,
  safetyDenied: 4,
  followUpsScheduled: 6,
  followUpsSent: 0,
  followUpsSkipped: 5,
};

export const domainAuthStatuses = [
  { label: "SPF", status: "demo read-only", state: "pending" as const },
  { label: "DKIM", status: "demo read-only", state: "pending" as const },
  { label: "DMARC", status: "demo read-only", state: "pending" as const },
];

export const warmupSteps = [
  { label: "Day 1", detail: "Mailbox added to local/demo warmup shell", state: "passed" as const },
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
