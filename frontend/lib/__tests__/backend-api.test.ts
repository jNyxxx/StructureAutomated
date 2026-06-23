import { describe, expect, it } from "vitest";

import { ApiError } from "../api-client";
import {
  mapBackendErrorToStatus,
  mapHealthResponseToStatus,
  parseAuthMeResponse,
} from "../backend-api";

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
