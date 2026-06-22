import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuditLogTable, formatSafeDetails } from "@/components/audit-log-table";
import { BillingBanner, readOnlyBillingStatus } from "@/components/billing-banner";
import { AuthGate, ClerkFrontendProvider, isLocalMockAuthAllowed } from "@/lib/clerk";
import { TenantProvider, TenantStatusCard } from "@/lib/tenant-context";

import AuditLogsPage from "../(app)/audit-logs/page";
import BillingPage from "../(app)/billing/page";
import DashboardPage from "../(app)/dashboard/page";
import LoginPage from "../(auth)/login/page";

describe("route shells render", () => {
  it("renders the Clerk login shell heading without password inputs", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeTruthy();
    expect(screen.queryByLabelText(/password/i)).toBeNull();
  });

  it("renders the dashboard shell heading", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeTruthy();
  });

  it("renders the billing shell and read-only banner", () => {
    render(<BillingPage />);
    expect(screen.getByRole("heading", { name: /billing/i })).toBeTruthy();
    expect(screen.getAllByText(/read only/i).length).toBeGreaterThan(0);
  });

  it("renders the audit log empty state", () => {
    render(<AuditLogsPage />);
    expect(screen.getByRole("heading", { name: /audit logs/i })).toBeTruthy();
    expect(screen.getByText(/no audit events yet/i)).toBeTruthy();
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

  it("does not assume tenant access until backend confirmation", () => {
    render(
      <TenantProvider initialTenantId="11111111-1111-1111-1111-111111111111">
        <TenantStatusCard />
      </TenantProvider>,
    );
    expect(screen.getByText(/not confirmed by the backend/i)).toBeTruthy();
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
