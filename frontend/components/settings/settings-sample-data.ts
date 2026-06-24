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
  { id: "team_001", name: "Demo Owner", email: "owner@example.com", role: "tenant_owner", mfaStatus: "enabled", status: "active", updatedAt: "local demo" },
  { id: "team_002", name: "Demo Admin", email: "admin@example.com", role: "tenant_admin", mfaStatus: "required", status: "invited", updatedAt: "local demo" },
  { id: "team_003", name: "Demo Viewer", email: "viewer@example.com", role: "viewer", mfaStatus: "pending", status: "locked", updatedAt: "local demo" },
];

export const integrations = [
  { name: "Email provider", description: "Future mailbox/provider connection for production sending.", status: "disabled", phase: "pending backend" },
  { name: "Stripe", description: "Real checkout/webhooks deferred until first paying client.", status: "disabled", phase: "deferred" },
  { name: "Twilio SMS", description: "SMS is post-MVP and not connected.", status: "post-MVP", phase: "post-MVP" },
  { name: "Google Ads", description: "Ads connectors are post-MVP.", status: "post-MVP", phase: "post-MVP" },
  { name: "Meta Ads", description: "Ads connectors are post-MVP.", status: "post-MVP", phase: "post-MVP" },
  { name: "Google Business Profile", description: "GBP production connector is post-MVP.", status: "post-MVP", phase: "post-MVP" },
  { name: "Live scraping", description: "Live scraping remains disabled for the MVP UI.", status: "disabled", phase: "post-MVP" },
];

export const suppressionRows: SuppressionRow[] = [
  { id: "sup_001", contact: "suppressed-demo@example.com", company: "Demo Realty C", reason: "Manual suppression", source: "local demo", status: "suppressed", updatedAt: "local demo" },
  { id: "sup_002", contact: "unsubscribe-demo@example.com", company: "Demo Assets B", reason: "Unsubscribe preview", source: "local demo", status: "unsubscribed", updatedAt: "local demo" },
  { id: "sup_003", contact: "blocked-demo@example.com", company: "Demo Office A", reason: "Safety denied", source: "local demo", status: "manual_block", updatedAt: "local demo" },
];
