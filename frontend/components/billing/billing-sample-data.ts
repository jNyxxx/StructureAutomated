export type MockBillingState = "trialing" | "active" | "past_due" | "canceled" | "unpaid" | "inactive";
export type DerivedGateKey = "can_send" | "can_run_agents" | "can_create_campaign" | "can_export";

export interface MockBillingStateRow {
  state: MockBillingState;
  tenantStatus: string;
  access: "allowed" | "limited" | "locked";
  note: string;
}

export const currentBilling = {
  tenant: "Automated Structure Demo Tenant",
  tenantStatus: "inactive",
  plan: "CRE Outreach MVP Demo",
  subscription: "mock_subscription_local_001",
  state: "inactive" as MockBillingState,
  usage: {
    prospects: { used: 69, limit: 250 },
    campaigns: { used: 3, limit: 10 },
    draftRuns: { used: 12, limit: 100 },
    exports: { used: 0, limit: 5 },
  },
};

export const mockBillingStates: MockBillingStateRow[] = [
  { state: "trialing", tenantStatus: "trial", access: "allowed", note: "Local mock access for demos only." },
  { state: "active", tenantStatus: "active", access: "allowed", note: "Would allow gated MVP features when backend confirms." },
  { state: "past_due", tenantStatus: "grace", access: "limited", note: "Grace-period behavior must be enforced by backend gates." },
  { state: "canceled", tenantStatus: "inactive", access: "locked", note: "No access to paid features." },
  { state: "unpaid", tenantStatus: "inactive", access: "locked", note: "No access until billing is resolved." },
  { state: "inactive", tenantStatus: "inactive", access: "locked", note: "Catch-all no-access state." },
];

export const derivedGates: Array<{ key: DerivedGateKey; label: string; allowed: boolean; reason: string }> = [
  { key: "can_send", label: "Can send", allowed: false, reason: "No real sending; tenant inactive; backend gate pending." },
  { key: "can_run_agents", label: "Can run agents", allowed: false, reason: "Research/RAG/agent APIs are not mounted." },
  { key: "can_create_campaign", label: "Can create campaign", allowed: false, reason: "Campaign mutation API pending." },
  { key: "can_export", label: "Can export", allowed: false, reason: "Export API pending and tenant inactive." },
];
