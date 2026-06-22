import { errorEnvelopeSchema } from "./schemas";

/** Typed error mapped from the backend standard error envelope. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(
    message: string,
    opts: {
      code: string;
      status: number;
      details?: Record<string, unknown>;
      requestId?: string | null;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.code = opts.code;
    this.status = opts.status;
    this.details = opts.details ?? {};
    this.requestId = opts.requestId ?? null;
  }
}

export interface ApiClientOptions {
  baseUrl?: string;
  /** Injectable fetch (used by tests); defaults to the global fetch. */
  fetchImpl?: typeof fetch;
}

const DEFAULT_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function toApiError(body: unknown, status: number): ApiError {
  const parsed = errorEnvelopeSchema.safeParse(body);
  if (parsed.success) {
    const err = parsed.data.error;
    return new ApiError(err.message, {
      code: err.code,
      status,
      details: err.details,
      requestId: err.request_id ?? null,
    });
  }
  // Non-envelope failure (network/proxy/unexpected): never surface raw bodies.
  return new ApiError("Request failed.", { code: "UNKNOWN", status, details: {}, requestId: null });
}

export async function apiRequest<T = unknown>(
  path: string,
  init: RequestInit = {},
  options: ApiClientOptions = {},
): Promise<T> {
  const baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;
  const doFetch = options.fetchImpl ?? fetch;

  const response = await doFetch(`${baseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });

  const raw = await response.text();
  let body: unknown;
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      body = raw;
    }
  }

  if (!response.ok) {
    throw toApiError(body, response.status);
  }
  return body as T;
}

export interface ApiClient {
  get<T = unknown>(path: string, options?: ApiClientOptions): Promise<T>;
  post<T = unknown>(path: string, body?: unknown, options?: ApiClientOptions): Promise<T>;
}

export function createApiClient(base: ApiClientOptions = {}): ApiClient {
  return {
    get: (path, options) => apiRequest(path, { method: "GET" }, { ...base, ...options }),
    post: (path, body, options) =>
      apiRequest(
        path,
        { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) },
        { ...base, ...options },
      ),
  };
}
