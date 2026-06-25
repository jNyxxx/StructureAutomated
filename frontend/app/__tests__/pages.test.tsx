import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuditLogTable, formatSafeDetails } from "@/components/audit-log-table";
import { BillingBanner, readOnlyBillingStatus } from "@/components/billing-banner";
import { AuthGate, ClerkFrontendProvider, isLocalMockAuthAllowed, type FrontendAuthState } from "@/lib/clerk";
import { TenantProvider, TenantStatusCard } from "@/lib/tenant-context";

import AuditLogsPage from "../(app)/audit-logs/page";
import BillingPage from "../(app)/billing/page";
import AiDraftsPage from "../(app)/ai-drafts/page";
import CampaignsPage from "../(app)/campaigns/page";
import CampaignDetailPage from "../(app)/campaigns/[id]/page";
import CampaignDraftsPage from "../(app)/campaigns/[id]/drafts/page";
import NewCampaignPage from "../(app)/campaigns/new/page";
import DashboardPage from "../(app)/dashboard/page";
import DeliverabilityPage from "../(app)/deliverability/page";
import OutcomesPage from "../(app)/outcomes/page";
import PrivacyPage from "../(app)/privacy/page";
import ProspectsPage from "../(app)/prospects/page";
import ProspectImportPage from "../(app)/prospects/import/page";
import ReviewQueuePage from "../(app)/review-queue/page";
import SettingsPage from "../(app)/settings/page";
import ComplianceSettingsPage from "../(app)/settings/compliance/page";
import IntegrationsSettingsPage from "../(app)/settings/integrations/page";
import SecuritySettingsPage from "../(app)/settings/security/page";
import SuppressionSettingsPage from "../(app)/settings/suppression/page";
import TeamSettingsPage from "../(app)/settings/team/page";
import LoginPage from "../(auth)/login/page";

const signedInAuth: FrontendAuthState = {
  isLoaded: true,
  isSignedIn: true,
  userId: "11111111-1111-1111-1111-111111111111",
  email: "owner@example.com",
  mode: "local_mock",
  getToken: async () => "token-sentinel",
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "x-request-id": "req_test" }),
    text: async () => JSON.stringify(body),
  } as Response;
}

function renderWithTenant(node: ReactNode) {
  return render(
    <ClerkFrontendProvider value={signedInAuth}>
      <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
        {node}
      </TenantProvider>
    </ClerkFrontendProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/ready")) return jsonResponse({ status: "ready" });
      if (path.includes("/api/v1/tenants/current")) {
        return jsonResponse({
          tenant: {
            id: "22222222-2222-2222-2222-222222222222",
            name: "Automated Structure Test Tenant",
            status: "active",
            settings: {
              timezone: "UTC",
              locale: "en-US",
            },
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
            mock_only: true,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/memberships")) {
        return jsonResponse({
          memberships: [
            {
              id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              user_id: "11111111-1111-1111-1111-111111111111",
              role: "tenant_owner",
              membership_version: 1,
              created_at: "2026-06-24T12:00:00Z",
              mock_only: true,
            },
          ],
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/audit-events")) {
        return jsonResponse({
          audit_events: [
            {
              id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
              event_type: "send_gate.blocked",
              actor_user_id: "11111111-1111-1111-1111-111111111111",
              object_type: "mock_send",
              object_id: "22222222-2222-2222-2222-222222222222",
              request_id: "req_test_audit_001",
              job_id: null,
              redacted_details: {
                reason: "production_not_approved",
                contact_hash: "hash_demo_only",
                api_key: "[REDACTED]",
              },
              created_at: "2026-06-24T12:00:00Z",
            },
          ],
          page: {
            next_cursor: null,
            limit: 25,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/compliance/profile")) {
        return jsonResponse({
          compliance_profile: {
            jurisdiction: "US",
            sending_review_required: true,
            live_sending_allowed: false,
            sms_allowed: false,
            mock_only: true,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/suppressions")) {
        return jsonResponse({
          suppressions: [
            {
              id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
              channel: "email",
              reason: "manual backend mock block",
              source: "mock_api",
              never_contact: true,
              created_at: "2026-06-24T12:00:00Z",
              revoked_at: null,
              active: true,
              mock_only: true,
            },
          ],
          page: {
            next_cursor: null,
            limit: 25,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/prospects")) {
        return jsonResponse({
          prospects: [
            {
              id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
              contact_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
              full_name: "Ava Santos",
              title: "Acquisitions Lead",
              email: "ava@northline.com",
              domain: "northline.com",
              company_name: "Northline Properties",
              created_at: "2026-06-24T12:00:00Z",
              updated_at: "2026-06-24T12:00:00Z",
              mock_only: true,
            },
          ],
          page: {
            next_cursor: null,
            limit: 25,
          },
          mock_only: true,
        });
      }
      if (path.includes("/auth/me")) {
        return jsonResponse({
          principal: {
            provider_user_id: "clerk_123",
            user_id: "11111111-1111-1111-1111-111111111111",
            email: "owner@example.com",
            tenant_id: "22222222-2222-2222-2222-222222222222",
            role: "tenant_owner",
            membership_version: 1,
            mfa_verified: true,
          },
        });
      }
      if (path.includes("/api/v1/billing/access")) {
        return jsonResponse({
          access: {
            is_active: true,
            can_send: true,
            can_run_agents: true,
            can_create_campaign: true,
            can_export: true,
            mock_only: true,
          },
        });
      }
      if (path.includes("/api/v1/billing/subscription")) {
        return jsonResponse({
          subscription: {
            plan: {
              key: "cre-demo",
              name: "CRE Outreach MVP Demo",
              features: {
                can_send: true,
                can_run_agents: true,
                can_create_campaign: true,
                can_export: true,
              },
              mock_only: true,
            },
            tenant_status: "active",
            grace_until: null,
            mock_only: true,
          },
        });
      }
      if (path.includes("/api/v1/usage")) {
        return jsonResponse({
          usage: {
            contacts_total: 69,
            contact_imports_total: 3,
            campaigns_total: 2,
            drafts_total: 15,
            outbound_mock_sent: 5,
            outbound_blocked: 0,
            send_gate_denied: 0,
            followups_mock_sent: 0,
            followups_skipped: 0,
            research_runs_total: 10,
            outcome_events_total: 0,
            mock_only: true,
          },
        });
      }
      return jsonResponse({ status: "ok" });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("route shells render", () => {
  it("renders the Clerk login shell heading without password inputs", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeTruthy();
    expect(screen.queryByLabelText(/password/i)).toBeNull();
  });

  it("renders the dashboard shell heading", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <DashboardPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeTruthy();
  });

  it("renders the billing shell and access model", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <BillingPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /billing/i })).toBeTruthy();
    expect(screen.getAllByText(/Real Stripe deferred/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Derived access gates/i)).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
  });

  it("renders the audit log DataTable demo safely", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <AuditLogsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /audit logs/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /audit log table/i })).toBeTruthy();
    expect(screen.getByText(/send_gate.blocked/i)).toBeTruthy();
    expect(screen.getByText(/Redaction visible/i)).toBeTruthy();
  });

  it("renders the privacy operations shell", () => {
    render(<PrivacyPage />);
    expect(screen.getByRole("heading", { name: /privacy/i })).toBeTruthy();
    expect(screen.getAllByText(/soft delete/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Vector purge/i).length).toBeGreaterThan(0);
  });

  it("renders the prospects DataTable demo safely", () => {
    renderWithTenant(<ProspectsPage />);
    expect(screen.getByRole("heading", { name: /^prospects$/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /prospects demo table/i })).toBeTruthy();
    expect(screen.getByText(/Northline Properties/i)).toBeTruthy();
  });

  it("renders the CSV import wizard shell", () => {
    render(<ProspectImportPage />);
    expect(screen.getByRole("heading", { name: /import prospects/i })).toBeTruthy();
    expect(screen.getAllByText(/Upload CSV/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: /csv import preview rows/i })).toBeTruthy();
  });

  it("renders the campaigns DataTable demo safely", () => {
    render(<CampaignsPage />);
    expect(screen.getByRole("heading", { name: /^campaigns$/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /campaigns demo table/i })).toBeTruthy();
    expect(screen.getByText(/CRE Multifamily Owner Outreach/i)).toBeTruthy();
  });

  it("renders a campaign detail shell", () => {
    render(<CampaignDetailPage params={{ id: "cre-multifamily-demo" }} />);
    expect(screen.getByRole("heading", { name: /CRE Multifamily Owner Outreach/i })).toBeTruthy();
    expect(screen.getByText(/Pipeline stage progress/i)).toBeTruthy();
  });

  it("renders the locked campaign builder shell", () => {
    render(<NewCampaignPage />);
    expect(screen.getByRole("heading", { name: /new campaign/i })).toBeTruthy();
    expect(screen.getByText(/Campaign builder shell/i)).toBeTruthy();
  });

  it("renders the AI drafts workbench shell", () => {
    render(<AiDraftsPage />);
    expect(screen.getByRole("heading", { name: /ai drafts/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /ai drafts demo table/i })).toBeTruthy();
    expect(screen.getByText(/Research\/RAG workbench/i)).toBeTruthy();
  });

  it("renders campaign-scoped draft shell", () => {
    render(<CampaignDraftsPage params={{ id: "cre-multifamily-demo" }} />);
    expect(screen.getByRole("heading", { name: /CRE Multifamily Owner Outreach drafts/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /ai drafts demo table/i })).toBeTruthy();
  });

  it("renders the review queue demo safely", () => {
    render(<ReviewQueuePage />);
    expect(screen.getByRole("heading", { name: /review queue/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /review queue demo table/i })).toBeTruthy();
    expect(screen.getByText(/Human approval never bypasses/i)).toBeTruthy();
  });

  it("renders the deliverability dashboard shell", () => {
    render(<DeliverabilityPage />);
    expect(screen.getByRole("heading", { name: /deliverability/i })).toBeTruthy();
    expect(screen.getAllByText(/Mailbox health/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/No real DNS checks/i)).toBeTruthy();
  });

  it("renders the outcomes ROI dashboard shell", () => {
    render(<OutcomesPage />);
    expect(screen.getByRole("heading", { name: /outcomes and ROI/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /campaign outcomes demo table/i })).toBeTruthy();
    expect(screen.getByText(/No real Stripe\/payment data/i)).toBeTruthy();
  });

  it("renders the settings hub shell", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <SettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /^settings$/i })).toBeTruthy();
    expect(screen.getAllByText(/Tenant profile settings/i).length).toBeGreaterThan(0);
  });

  it("renders team settings table shell", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <TeamSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /team settings/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /team members table/i })).toBeTruthy();
  });

  it("renders integrations settings shell", () => {
    render(<IntegrationsSettingsPage />);
    expect(screen.getByRole("heading", { name: /integrations/i })).toBeTruthy();
    expect(screen.getByText(/No real provider\/OAuth calls/i)).toBeTruthy();
  });

  it("renders security settings shell", () => {
    render(<SecuritySettingsPage />);
    expect(screen.getByRole("heading", { name: /security settings/i })).toBeTruthy();
    expect(screen.getAllByText(/Production JWT verifier/i).length).toBeGreaterThan(0);
  });

  it("renders compliance settings shell", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <ComplianceSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /compliance settings/i })).toBeTruthy();
    expect(screen.getByText(/US-first baseline/i)).toBeTruthy();
  });

  it("loads compliance settings from the backend mock API while actions stay locked", async () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <ComplianceSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/Compliance profile loaded from backend mock API/i)).toBeTruthy());
    expect(screen.getByText(/Compliance API read-only/i)).toBeTruthy();
    expect(screen.getByText(/No real sending/i)).toBeTruthy();
  });

  it("renders compliance fixture fallback when backend auth is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <ComplianceSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/Backend unavailable or auth missing/i)).toBeTruthy());
  });

  it("renders suppression settings table shell", () => {
    renderWithTenant(<SuppressionSettingsPage />);
    expect(screen.getByRole("heading", { name: /suppression settings/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /suppression demo table/i })).toBeTruthy();
  });

  it("loads suppressions from the backend mock API while actions stay locked", async () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <SuppressionSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/manual backend mock block/i)).toBeTruthy());
    expect(screen.getByText(/Suppression API read-only/i)).toBeTruthy();
    expect(screen.getByText(/Add suppression locked/i)).toBeTruthy();
  });

  it("renders suppression fixture fallback when backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <SuppressionSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/fixture fallback/i)).toBeTruthy());
    expect(screen.getByText(/suppressed-demo@example.com/i)).toBeTruthy();
  });
});

describe("phase 0 frontend wiring components", () => {
  it("proves local/mock auth is not allowed in production by default", () => {
    expect(isLocalMockAuthAllowed("production", undefined)).toBe(false);
    expect(isLocalMockAuthAllowed("production", "true")).toBe(true);
    expect(isLocalMockAuthAllowed("development", undefined)).toBe(true);
  });

  it("protects app routes when Clerk auth is not signed in", () => {
    render(
      <ClerkFrontendProvider>
        <AuthGate>
          <div>Protected content</div>
        </AuthGate>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByText(/authentication required/i)).toBeTruthy();
    expect(screen.queryByText(/protected content/i)).toBeNull();
  });

  it("shows session unavailable when auth is not signed in", async () => {
    render(
      <ClerkFrontendProvider>
        <TenantProvider initialTenantId="11111111-1111-1111-1111-111111111111">
          <TenantStatusCard />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByText(/session unavailable/i)).toBeTruthy());
  });

  it("loads tenant context from /auth/me when auth shell is signed in", async () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider>
          <TenantStatusCard />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/tenant access confirmed/i)).toBeTruthy());
    expect(screen.getByText(/tenant_owner/i)).toBeTruthy();
  });

  it("shows central billing gates in locked/read-only mode", () => {
    render(<BillingBanner status={readOnlyBillingStatus} />);
    expect(screen.getByText(/billing: unknown/i)).toBeTruthy();
    expect(screen.getAllByText(/locked/i).length).toBeGreaterThan(0);
  });

  it("only formats safe audit detail keys", () => {
    expect(formatSafeDetails({ scope: "read:audit", token: "sentinel", contact_hash: "hash" })).toBe(
      "scope: read:audit",
    );
  });

  it("renders audit denied state safely", () => {
    render(<AuditLogTable events={[]} state="denied" />);
    expect(screen.getByText(/access denied/i)).toBeTruthy();
  });
});
