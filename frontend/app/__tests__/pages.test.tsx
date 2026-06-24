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

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/ready")) return jsonResponse({ status: "ready" });
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
    render(<BillingPage />);
    expect(screen.getByRole("heading", { name: /billing/i })).toBeTruthy();
    expect(screen.getAllByText(/Real Stripe deferred/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Derived access gates/i)).toBeTruthy();
  });

  it("renders the audit log DataTable demo safely", () => {
    render(<AuditLogsPage />);
    expect(screen.getByRole("heading", { name: /audit logs/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /audit log demo table/i })).toBeTruthy();
    expect(screen.getByText(/send_gate.blocked/i)).toBeTruthy();
  });

  it("renders the prospects DataTable demo safely", () => {
    render(<ProspectsPage />);
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
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { name: /^settings$/i })).toBeTruthy();
    expect(screen.getByText(/Tenant profile shell/i)).toBeTruthy();
  });

  it("renders team settings table shell", () => {
    render(<TeamSettingsPage />);
    expect(screen.getByRole("heading", { name: /team settings/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /team members demo table/i })).toBeTruthy();
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
    render(<ComplianceSettingsPage />);
    expect(screen.getByRole("heading", { name: /compliance settings/i })).toBeTruthy();
    expect(screen.getByText(/US-first compliance baseline/i)).toBeTruthy();
  });

  it("renders suppression settings table shell", () => {
    render(<SuppressionSettingsPage />);
    expect(screen.getByRole("heading", { name: /suppression settings/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /suppression demo table/i })).toBeTruthy();
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
