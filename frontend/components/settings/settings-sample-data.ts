export type TeamRole = "platform_admin" | "tenant_owner" | "tenant_admin" | "member" | "viewer";

export interface TeamMemberRow {
  id: string;
  name: string;
  email: string;
  role: TeamRole;
  mfaStatus: "enabled" | "pending" | "required";
  status: "active" | "invited" | "locked";
  updatedAt: string;
}

export interface SuppressionRow {
  id: string;
  contact: string;
  company: string;
  reason: string;
  source: string;
  status: "suppressed" | "unsubscribed" | "manual_block";
  updatedAt: string;
}

export const teamMembers: TeamMemberRow[] = [
  { id: "team_001", name: "Demo Owner", email: "owner@example.com", role: "tenant_owner", mfaStatus: "enabled", status: "active", updatedAt: "2026-06-24" },
  { id: "team_002", name: "Demo Admin", email: "admin@example.com", role: "tenant_admin", mfaStatus: "required", status: "invited", updatedAt: "2026-06-24" },
  { id: "team_003", name: "Demo Viewer", email: "viewer@example.com", role: "viewer", mfaStatus: "pending", status: "locked", updatedAt: "2026-06-24" },
];

export const integrations = [
  { name: "Email provider", description: "Primary SMTP/IMAP/API mailbox provider connection.", status: "Connected", phase: "Production" },
  { name: "Stripe", description: "Production billing and customer invoice portal.", status: "Connected", phase: "Production" },
  { name: "Twilio SMS", description: "Outbound SMS verification and alert alerts.", status: "Connected", phase: "Production" },
  { name: "Google Ads", description: "Google Ads platform connector for attribution mapping.", status: "Connected", phase: "Production" },
  { name: "Meta Ads", description: "Meta Ads campaign tracker and target list sync.", status: "Connected", phase: "Production" },
  { name: "Google Business Profile", description: "Local search and profile review monitoring.", status: "Connected", phase: "Production" },
  { name: "Live scraping", description: "Web scraper enrichment pipeline.", status: "Connected", phase: "Production" },
];

export const suppressionRows: SuppressionRow[] = [
  { id: "sup_001", contact: "suppressed-demo@example.com", company: "Demo Realty C", reason: "Manual suppression", source: "Compliance Dashboard", status: "suppressed", updatedAt: "2026-06-24" },
  { id: "sup_002", contact: "unsubscribe-demo@example.com", company: "Demo Assets B", reason: "Unsubscribe link clicked", source: "Outreach Email", status: "unsubscribed", updatedAt: "2026-06-24" },
  { id: "sup_003", contact: "blocked-demo@example.com", company: "Demo Office A", reason: "Safety filter block", source: "Global Rule Engine", status: "manual_block", updatedAt: "2026-06-24" },
];
