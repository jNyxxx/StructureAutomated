import { describe, expect, it } from "vitest";

import { ApiError, apiRequest } from "../api-client";

/** Build a fetch stub exposing only what the client uses (ok/status/text). */
function mockFetch(status: number, body: unknown): typeof fetch {
  const fake = {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  };
  return (async () => fake as unknown as Response) as unknown as typeof fetch;
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
    expect(err.details.field).toBe("tenant_id");
  });

  it("falls back to UNKNOWN for a non-envelope error body", async () => {
    let caught: unknown;
    try {
      await apiRequest("/x", {}, { fetchImpl: mockFetch(500, "raw gateway text") });
    } catch (error) {
      caught = error;
    }
    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("UNKNOWN");
    expect(err.status).toBe(500);
    // Raw upstream body must not leak into the surfaced message.
    expect(err.message).toBe("Request failed.");
  });
});
