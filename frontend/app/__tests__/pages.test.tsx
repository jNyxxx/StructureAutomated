import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuditLogTable, formatSafeDetails } from "@/components/audit-log-table";
import { BillingBanner, readOnlyBillingStatus } from "@/components/billing-banner";
import { AuthGate, ClerkFrontendProvider, isLocalMockAuthAllowed, type FrontendAuthState } from "@/lib/clerk";
import { TenantProvider, TenantStatusCard } from "@/lib/tenant-context";

import AuditLogsPage from "../(app)/audit-logs/page";
import BillingPage from "../(app)/billing/page";
import DashboardPage from "../(app)/dashboard/page";
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

  it("renders the billing shell and read-only banner", () => {
    render(<BillingPage />);
    expect(screen.getByRole("heading", { name: /billing/i })).toBeTruthy();
    expect(screen.getAllByText(/read only/i).length).toBeGreaterThan(0);
  });

  it("renders the audit log DataTable demo safely", () => {
    render(<AuditLogsPage />);
    expect(screen.getByRole("heading", { name: /audit logs/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /audit log demo table/i })).toBeTruthy();
    expect(screen.getByText(/send_gate.blocked/i)).toBeTruthy();
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
