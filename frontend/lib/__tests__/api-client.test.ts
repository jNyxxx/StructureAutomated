import { describe, expect, it } from "vitest";

import { ApiError, apiRequest, authenticatedApiRequest } from "../api-client";

/** Build a fetch stub exposing only what the client uses. */
function mockFetch(
  status: number,
  body: unknown,
  capture?: (input: RequestInfo | URL, init?: RequestInit) => void,
  headers: Record<string, string> = {},
): typeof fetch {
  const fake = {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  };
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    capture?.(input, init);
    return fake as unknown as Response;
  }) as unknown as typeof fetch;
}

describe("apiRequest", () => {
  it("returns parsed JSON on a successful response", async () => {
    const data = await apiRequest<{ status: string }>(
      "/health",
      {},
      { fetchImpl: mockFetch(200, { status: "ok" }) },
    );
    expect(data.status).toBe("ok");
  });

  it("throws an ApiError mapped from the standard error envelope", async () => {
    const envelope = {
      error: {
        code: "PERMISSION_DENIED",
        message: "You do not have access.",
        details: { field: "tenant_id" },
        request_id: "req_abc123",
        correlation_id: "corr_abc123",
      },
    };

    let caught: unknown;
    try {
      await apiRequest("/secret", {}, { fetchImpl: mockFetch(403, envelope) });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.message).toBe("You do not have access.");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_abc123");
    expect(err.correlationId).toBe("corr_abc123");
    expect(err.details.field).toBe("tenant_id");
  });

  it("extracts request and correlation IDs from headers when the body is not an envelope", async () => {
    let caught: unknown;
    try {
      await apiRequest(
        "/x",
        {},
        { fetchImpl: mockFetch(500, "raw gateway text", undefined, { "x-request-id": "req_header", "x-correlation-id": "corr_header" }) },
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("UNKNOWN");
    expect(err.status).toBe(500);
    expect(err.message).toBe("Request failed.");
    expect(err.requestId).toBe("req_header");
    expect(err.correlationId).toBe("corr_header");
  });

  it("falls back to NETWORK_ERROR without leaking transport details", async () => {
    const fetchImpl = (async () => {
      throw new Error("socket secret sentinel");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await apiRequest("/ready", {}, { fetchImpl });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
    expect(err.message).toBe("Request failed.");
  });

  it("attaches Clerk bearer token and selected tenant header without exposing token", async () => {
    let captured: RequestInit | undefined;
    const data = await authenticatedApiRequest<{ ok: boolean }>(
      "/auth/me",
      { method: "GET" },
      {
        fetchImpl: mockFetch(200, { ok: true }, (_input, init) => {
          captured = init;
        }),
        getToken: async () => "clerk-token-sentinel",
        getTenantId: () => "11111111-1111-1111-1111-111111111111",
      },
    );

    const headers = new Headers(captured?.headers);
    expect(data.ok).toBe(true);
    expect(headers.get("Authorization")).toBe("Bearer clerk-token-sentinel");
    expect(headers.get("X-Tenant-ID")).toBe("11111111-1111-1111-1111-111111111111");
  });
});
