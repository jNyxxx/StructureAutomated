import { describe, expect, it } from "vitest";

import { ApiError } from "../api-client";
import {
  fetchBillingAccess,
  fetchBillingSubscription,
  fetchUsage,
  mapBackendErrorToStatus,
  mapHealthResponseToStatus,
  parseAuthMeResponse,
} from "../backend-api";

/** Build a fetch stub exposing only what the client uses. */
function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}): typeof fetch {
  const fake = {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  };
  return (async () => fake as unknown as Response) as unknown as typeof fetch;
}

function authOptions(fetchImpl: typeof fetch) {
  return {
    fetchImpl,
    getToken: async () => "token-sentinel",
    getTenantId: () => "22222222-2222-2222-2222-222222222222",
  };
}

describe("backend status mapping", () => {
  it("maps ready success without claiming production readiness", () => {
    const status = mapHealthResponseToStatus({ status: "ready", request_id: "req_ready" }, "ready");

    expect(status.state).toBe("healthy");
    expect(status.label).toBe("Backend ready");
    expect(status.message).toContain("not production approval");
    expect(status.requestId).toBe("req_ready");
  });

  it("maps ready failures to unavailable/degraded-safe UI", () => {
    const status = mapBackendErrorToStatus(
      new ApiError("Request failed.", { code: "NETWORK_ERROR", status: 0, requestId: "req_down" }),
      "ready",
    );

    expect(status.state).toBe("unavailable");
    expect(status.label).toBe("Backend readiness unavailable");
    expect(status.requestId).toBe("req_down");
  });
});

describe("auth response parsing", () => {
  it("parses /auth/me principal response", () => {
    const parsed = parseAuthMeResponse({
      principal: {
        provider_user_id: "clerk_123",
        user_id: "11111111-1111-1111-1111-111111111111",
        email: "owner@example.com",
        tenant_id: "22222222-2222-2222-2222-222222222222",
        role: "tenant_owner",
        membership_version: 3,
        mfa_verified: true,
      },
    });

    expect(parsed.principal.tenant_id).toBe("22222222-2222-2222-2222-222222222222");
    expect(parsed.principal.role).toBe("tenant_owner");
  });
});

describe("billing/usage read fetchers (read-only)", () => {
  it("fetchBillingSubscription parses a mock subscription and preserves mock_only", async () => {
    const res = await fetchBillingSubscription(
      authOptions(
        mockFetch(200, {
          subscription: {
            plan: { key: "cre-demo", name: "CRE Outreach MVP Demo", features: { can_send: true }, mock_only: true },
            tenant_status: "active",
            grace_until: null,
            mock_only: true,
          },
        }),
      ),
    );

    expect(res.subscription.tenant_status).toBe("active");
    expect(res.subscription.mock_only).toBe(true);
  });

  it("fetchBillingAccess parses mock access gates and preserves mock_only", async () => {
    const res = await fetchBillingAccess(
      authOptions(
        mockFetch(200, {
          access: {
            is_active: true,
            can_send: true,
            can_run_agents: true,
            can_create_campaign: true,
            can_export: true,
            mock_only: true,
          },
        }),
      ),
    );

    expect(res.access.can_send).toBe(true);
    expect(res.access.mock_only).toBe(true);
  });

  it("fetchUsage parses a mock usage snapshot and preserves mock_only", async () => {
    const res = await fetchUsage(
      authOptions(
        mockFetch(200, {
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
        }),
      ),
    );

    expect(res.usage.contacts_total).toBe(69);
    expect(res.usage.mock_only).toBe(true);
  });

  it("maps a backend error envelope to a typed ApiError without leaking the body", async () => {
    let caught: unknown;
    try {
      await fetchUsage(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "You do not have access.",
              details: { field: "tenant_id" },
              request_id: "req_usage",
              correlation_id: "corr_usage",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_usage");
  });

  it("maps a transport failure to NETWORK_ERROR with status 0", async () => {
    const failing = (async () => {
      throw new Error("socket secret sentinel");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchBillingSubscription(authOptions(failing));
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
    expect(err.message).toBe("Request failed.");
  });
});
