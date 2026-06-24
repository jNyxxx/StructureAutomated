import { z } from "zod";

import { ApiError, apiRequest, authenticatedApiRequest, type AuthenticatedApiClientOptions, type ApiClientOptions } from "./api-client";
import { authMeResponseSchema, healthResponseSchema, type AuthMeResponse, type HealthResponse } from "./schemas";

export type BackendAvailability = "healthy" | "degraded" | "unavailable" | "unknown";

export interface BackendStatusView {
  state: BackendAvailability;
  label: string;
  message: string;
  requestId: string | null;
  correlationId: string | null;
  rawStatus: string | null;
}

export async function fetchHealth(options: ApiClientOptions = {}): Promise<HealthResponse> {
  return healthResponseSchema.parse(await apiRequest("/health", { method: "GET" }, options));
}

export async function fetchLive(options: ApiClientOptions = {}): Promise<HealthResponse> {
  return healthResponseSchema.parse(await apiRequest("/live", { method: "GET" }, options));
}

export async function fetchReady(options: ApiClientOptions = {}): Promise<HealthResponse> {
  return healthResponseSchema.parse(await apiRequest("/ready", { method: "GET" }, options));
}

export async function fetchAuthMe(options: AuthenticatedApiClientOptions): Promise<AuthMeResponse> {
  return authMeResponseSchema.parse(await authenticatedApiRequest("/auth/me", { method: "GET" }, options));
}

export async function logout(options: AuthenticatedApiClientOptions): Promise<void> {
  await authenticatedApiRequest("/auth/logout", { method: "POST" }, options);
}

export async function logoutAll(options: AuthenticatedApiClientOptions): Promise<void> {
  await authenticatedApiRequest("/auth/logout-all", { method: "POST" }, options);
}

export function mapHealthResponseToStatus(response: HealthResponse, target: "health" | "ready" = "health"): BackendStatusView {
  const rawStatus = typeof response.status === "string" ? response.status : null;
  const normalized = rawStatus?.toLowerCase() ?? (response.ok === true ? "ok" : null);
  const readyHealthy = normalized === "ready" || normalized === "ok" || normalized === "healthy" || normalized === "live";
  const degraded = normalized === "degraded" || normalized === "warning" || normalized === "partial";

  if (readyHealthy) {
    return {
      state: "healthy",
      label: target === "ready" ? "Backend ready" : "Backend healthy",
      message: target === "ready" ? "Local backend readiness endpoint responded. This is not production approval." : "Local backend health endpoint responded.",
      requestId: response.request_id ?? null,
      correlationId: response.correlation_id ?? null,
      rawStatus,
    };
  }

  if (degraded) {
    return {
      state: "degraded",
      label: "Backend degraded",
      message: "The backend responded but reported a degraded local state. Keep unavailable actions locked.",
      requestId: response.request_id ?? null,
      correlationId: response.correlation_id ?? null,
      rawStatus,
    };
  }

  return {
    state: "unknown",
    label: "Backend status unknown",
    message: "The backend responded with an unrecognized local status. Do not treat this as production readiness.",
    requestId: response.request_id ?? null,
    correlationId: response.correlation_id ?? null,
    rawStatus,
  };
}

export function mapBackendErrorToStatus(error: unknown, target: "health" | "ready" = "ready"): BackendStatusView {
  if (error instanceof ApiError) {
    return {
      state: "unavailable",
      label: target === "ready" ? "Backend readiness unavailable" : "Backend health unavailable",
      message: "The local backend endpoint failed or is unreachable. Keep dependent actions degraded/locked.",
      requestId: error.requestId,
      correlationId: error.correlationId,
      rawStatus: error.code,
    };
  }

  return {
    state: "unavailable",
    label: "Backend unavailable",
    message: "The local backend endpoint could not be reached. Keep dependent actions degraded/locked.",
    requestId: null,
    correlationId: null,
    rawStatus: null,
  };
}

export function parseAuthMeResponse(body: unknown): AuthMeResponse {
  return authMeResponseSchema.parse(body);
}

export function isAuthMeResponse(body: unknown): body is AuthMeResponse {
  return authMeResponseSchema.safeParse(body).success;
}

export function parseHealthResponse(body: unknown): HealthResponse {
  return healthResponseSchema.parse(body);
}

export function formatZodError(error: z.ZodError): string {
  return error.issues.map((issue) => issue.message).join(", ");
}
