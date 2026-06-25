import { z } from "zod";

import { ApiError, apiRequest, authenticatedApiRequest, type AuthenticatedApiClientOptions, type ApiClientOptions } from "./api-client";
import {
  authMeResponseSchema,
  healthResponseSchema,
  billingSubscriptionResponseSchema,
  billingAccessResponseSchema,
  usageResponseSchema,
  tenantResponseSchema,
  membershipListResponseSchema,
  auditEventListResponseSchema,
  complianceProfileResponseSchema,
  suppressionListResponseSchema,
  contactListResponseSchema,
  prospectListResponseSchema,
  contactDetailResponseSchema,
  campaignListResponseSchema,
  campaignDetailResponseSchema,
  draftDetailResponseSchema,
  draftEvidenceListResponseSchema,
  reviewItemListResponseSchema,
  reviewItemDetailResponseSchema,
  deliverabilityResponseSchema,
  mailboxHealthResponseSchema,
  outcomesResponseSchema,
  roiResponseSchema,
  contactImportResponseSchema,
  campaignActionResponseSchema,
  campaignContactSelectionResponseSchema,
  draftGenerateResponseSchema,
  reviewActionResponseSchema,
  sendGateDryRunResponseSchema,
  sendIntentResponseSchema,
  followUpRuleActionResponseSchema,
  followUpScheduleActionResponseSchema,
  suppressionActionResponseSchema,
  tenantUpdateResponseSchema,
  complianceProfileActionResponseSchema,
  mockOutcomeEventResponseSchema,
  type AuthMeResponse,
  type HealthResponse,
  type BillingSubscriptionResponse,
  type BillingAccessResponse,
  type UsageResponse,
  type TenantResponse,
  type MembershipListResponse,
  type AuditEventListResponse,
  type ComplianceProfileResponse,
  type SuppressionListResponse,
  type ContactListResponse,
  type ProspectListResponse,
  type ContactDetailResponse,
  type CampaignListResponse,
  type CampaignDetailResponse,
  type DraftDetailResponse,
  type DraftEvidenceListResponse,
  type ReviewItemListResponse,
  type ReviewItemDetailResponse,
  type DeliverabilityResponse,
  type MailboxHealthResponse,
  type OutcomesResponse,
  type RoiResponse,
  type ContactImportResponse,
  type CampaignActionResponse,
  type CampaignContactSelectionResponse,
  type DraftGenerateResponse,
  type ReviewActionResponse,
  type SendGateDryRunResponse,
  type SendIntentResponse,
  type FollowUpRuleActionResponse,
  type FollowUpScheduleActionResponse,
  type SuppressionActionResponse,
  type TenantUpdateResponse,
  type ComplianceProfileActionResponse,
  type MockOutcomeEventResponse,
} from "./schemas";

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

export interface IdempotentApiClientOptions extends AuthenticatedApiClientOptions {
  idempotencyKey?: string;
}

export interface ContactImportRequest {
  csv_text: string;
  source_filename?: string | null;
}

export interface CampaignCreateRequest {
  name: string;
  description?: string | null;
  goal?: string | null;
  target_segment?: string | null;
  notes?: string | null;
}

export interface CampaignUpdateRequest {
  name?: string | null;
  description?: string | null;
  goal?: string | null;
  target_segment?: string | null;
  notes?: string | null;
  status?: string | null;
}

export interface CampaignContactSelectRequest {
  contact_id: string;
  status?: string;
}

export interface DraftGenerateRequest {
  campaign_id: string;
  contact_id: string;
}

export interface ReviewActionRequest {
  reason?: string | null;
}

export interface SendGateDryRunRequest {
  draft_id: string;
}

export interface SendIntentRequest {
  draft_id: string;
}

export interface FollowUpRuleCreateRequest {
  campaign_id: string;
  delay_seconds: number;
}

export interface FollowUpScheduleCreateRequest {
  original_outbound_message_id: string;
}

export interface SuppressionCreateRequest {
  channel?: string;
  contact_identifier: string;
  reason: string;
  source?: string;
  never_contact?: boolean;
}

export interface TenantUpdateRequest {
  name?: string | null;
  settings?: Record<string, unknown> | null;
}

export interface ComplianceProfileUpdateRequest {
  jurisdiction?: string;
  sending_review_required?: boolean;
  live_sending_allowed?: boolean;
  sms_allowed?: boolean;
}

export interface MockOutcomeEventRequest {
  campaign_id: string;
  contact_id: string;
  event_type: string;
  outbound_message_id?: string | null;
  note?: string | null;
  occurred_at?: string | null;
}

function createIdempotencyKey(operation: string): string {
  const random = globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);
  return `as-${operation}-${random}`;
}

function idempotencyHeaders(operation: string, key?: string): HeadersInit {
  return { "Idempotency-Key": key ?? createIdempotencyKey(operation) };
}

async function authenticatedIdempotentRequest<T>(
  path: string,
  method: "POST" | "PATCH" | "PUT",
  body: unknown,
  options: IdempotentApiClientOptions,
  operation: string,
): Promise<T> {
  return authenticatedApiRequest(
    path,
    {
      method,
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: idempotencyHeaders(operation, options.idempotencyKey),
    },
    options,
  );
}

export async function fetchBillingSubscription(options: AuthenticatedApiClientOptions): Promise<BillingSubscriptionResponse> {
  return billingSubscriptionResponseSchema.parse(
    await authenticatedApiRequest("/api/v1/billing/subscription", { method: "GET" }, options)
  );
}

export async function fetchBillingAccess(options: AuthenticatedApiClientOptions): Promise<BillingAccessResponse> {
  return billingAccessResponseSchema.parse(
    await authenticatedApiRequest("/api/v1/billing/access", { method: "GET" }, options)
  );
}

export async function fetchUsage(options: AuthenticatedApiClientOptions): Promise<UsageResponse> {
  return usageResponseSchema.parse(
    await authenticatedApiRequest("/api/v1/usage", { method: "GET" }, options)
  );
}

export async function fetchTenantSettings(options: AuthenticatedApiClientOptions): Promise<TenantResponse> {
  return tenantResponseSchema.parse(
    await authenticatedApiRequest("/api/v1/tenants/current", { method: "GET" }, options)
  );
}

export async function fetchMemberships(options: AuthenticatedApiClientOptions): Promise<MembershipListResponse> {
  return membershipListResponseSchema.parse(
    await authenticatedApiRequest("/api/v1/memberships", { method: "GET" }, options)
  );
}

export async function fetchAuditEvents(
  options: AuthenticatedApiClientOptions,
  params?: { cursor?: string | null; limit?: number }
): Promise<AuditEventListResponse> {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const queryString = query.toString();
  const path = `/api/v1/audit-events${queryString ? `?${queryString}` : ""}`;
  return auditEventListResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchComplianceProfile(options: AuthenticatedApiClientOptions): Promise<ComplianceProfileResponse> {
  return complianceProfileResponseSchema.parse(
    await authenticatedApiRequest("/api/v1/compliance/profile", { method: "GET" }, options)
  );
}

export async function fetchSuppressions(
  options: AuthenticatedApiClientOptions,
  params?: { cursor?: string | null; limit?: number }
): Promise<SuppressionListResponse> {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const queryString = query.toString();
  const path = `/api/v1/suppressions${queryString ? `?${queryString}` : ""}`;
  return suppressionListResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchContacts(
  options: AuthenticatedApiClientOptions,
  params?: { cursor?: string | null; limit?: number }
): Promise<ContactListResponse> {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const queryString = query.toString();
  const path = `/api/v1/contacts${queryString ? `?${queryString}` : ""}`;
  return contactListResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchProspects(
  options: AuthenticatedApiClientOptions,
  params?: { cursor?: string | null; limit?: number }
): Promise<ProspectListResponse> {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const queryString = query.toString();
  const path = `/api/v1/prospects${queryString ? `?${queryString}` : ""}`;
  return prospectListResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchContact(
  options: AuthenticatedApiClientOptions,
  contactId: string,
): Promise<ContactDetailResponse> {
  return contactDetailResponseSchema.parse(
    await authenticatedApiRequest(`/api/v1/contacts/${contactId}`, { method: "GET" }, options)
  );
}

export async function fetchCampaigns(
  options: AuthenticatedApiClientOptions,
  params?: { cursor?: string | null; limit?: number }
): Promise<CampaignListResponse> {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const queryString = query.toString();
  const path = `/api/v1/campaigns${queryString ? `?${queryString}` : ""}`;
  return campaignListResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchCampaign(
  options: AuthenticatedApiClientOptions,
  campaignId: string,
): Promise<CampaignDetailResponse> {
  return campaignDetailResponseSchema.parse(
    await authenticatedApiRequest(`/api/v1/campaigns/${campaignId}`, { method: "GET" }, options)
  );
}

export async function fetchDraft(
  options: AuthenticatedApiClientOptions,
  draftId: string,
): Promise<DraftDetailResponse> {
  return draftDetailResponseSchema.parse(
    await authenticatedApiRequest(`/api/v1/drafts/${draftId}`, { method: "GET" }, options)
  );
}

export async function fetchDraftEvidence(
  options: AuthenticatedApiClientOptions,
  draftId: string,
  params?: { cursor?: string | null; limit?: number },
): Promise<DraftEvidenceListResponse> {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const queryString = query.toString();
  const path = `/api/v1/drafts/${draftId}/evidence${queryString ? `?${queryString}` : ""}`;
  return draftEvidenceListResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchReviewItems(
  options: AuthenticatedApiClientOptions,
  params?: { cursor?: string | null; limit?: number; campaignId?: string | null; status?: string | null }
): Promise<ReviewItemListResponse> {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.campaignId) query.set("campaign_id", params.campaignId);
  if (params?.status) query.set("status", params.status);
  const queryString = query.toString();
  const path = `/api/v1/review/items${queryString ? `?${queryString}` : ""}`;
  return reviewItemListResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchReviewItem(
  options: AuthenticatedApiClientOptions,
  reviewId: string,
): Promise<ReviewItemDetailResponse> {
  return reviewItemDetailResponseSchema.parse(
    await authenticatedApiRequest(`/api/v1/review/items/${reviewId}`, { method: "GET" }, options)
  );
}

export async function fetchDeliverability(
  options: AuthenticatedApiClientOptions,
  params?: { campaignId?: string | null; dateFrom?: string | null; dateTo?: string | null },
): Promise<DeliverabilityResponse> {
  const query = new URLSearchParams();
  if (params?.campaignId) query.set("campaign_id", params.campaignId);
  if (params?.dateFrom) query.set("date_from", params.dateFrom);
  if (params?.dateTo) query.set("date_to", params.dateTo);
  const queryString = query.toString();
  const path = `/api/v1/deliverability${queryString ? `?${queryString}` : ""}`;
  return deliverabilityResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchDeliverabilityMailboxes(
  options: AuthenticatedApiClientOptions,
): Promise<MailboxHealthResponse> {
  return mailboxHealthResponseSchema.parse(
    await authenticatedApiRequest("/api/v1/deliverability/mailboxes", { method: "GET" }, options)
  );
}

export async function fetchOutcomes(
  options: AuthenticatedApiClientOptions,
  params?: { campaignId?: string | null; dateFrom?: string | null; dateTo?: string | null },
): Promise<OutcomesResponse> {
  const query = new URLSearchParams();
  if (params?.campaignId) query.set("campaign_id", params.campaignId);
  if (params?.dateFrom) query.set("date_from", params.dateFrom);
  if (params?.dateTo) query.set("date_to", params.dateTo);
  const queryString = query.toString();
  const path = `/api/v1/outcomes${queryString ? `?${queryString}` : ""}`;
  return outcomesResponseSchema.parse(
    await authenticatedApiRequest(path, { method: "GET" }, options)
  );
}

export async function fetchOutcomesRoi(
  options: AuthenticatedApiClientOptions,
  campaignId: string,
): Promise<RoiResponse> {
  const query = new URLSearchParams({ campaign_id: campaignId });
  return roiResponseSchema.parse(
    await authenticatedApiRequest(`/api/v1/outcomes/roi?${query.toString()}`, { method: "GET" }, options)
  );
}

export async function importContacts(
  options: IdempotentApiClientOptions,
  body: ContactImportRequest,
): Promise<ContactImportResponse> {
  return contactImportResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/imports/contacts", "POST", body, options, "imports-contacts")
  );
}

export async function createCampaign(
  options: IdempotentApiClientOptions,
  body: CampaignCreateRequest,
): Promise<CampaignActionResponse> {
  return campaignActionResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/campaigns", "POST", body, options, "campaigns-create")
  );
}

export async function updateCampaign(
  options: IdempotentApiClientOptions,
  campaignId: string,
  body: CampaignUpdateRequest,
): Promise<CampaignActionResponse> {
  return campaignActionResponseSchema.parse(
    await authenticatedIdempotentRequest(`/api/v1/campaigns/${campaignId}`, "PATCH", body, options, "campaigns-update")
  );
}

export async function selectCampaignContact(
  options: IdempotentApiClientOptions,
  campaignId: string,
  body: CampaignContactSelectRequest,
): Promise<CampaignContactSelectionResponse> {
  return campaignContactSelectionResponseSchema.parse(
    await authenticatedIdempotentRequest(`/api/v1/campaigns/${campaignId}/contacts`, "POST", body, options, "campaigns-contacts")
  );
}

export async function generateDraft(
  options: IdempotentApiClientOptions,
  body: DraftGenerateRequest,
): Promise<DraftGenerateResponse> {
  return draftGenerateResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/drafts/generate", "POST", body, options, "drafts-generate")
  );
}

export async function approveReviewItem(
  options: IdempotentApiClientOptions,
  reviewId: string,
  body: ReviewActionRequest = {},
): Promise<ReviewActionResponse> {
  return reviewActionResponseSchema.parse(
    await authenticatedIdempotentRequest(`/api/v1/review/items/${reviewId}/approve`, "POST", body, options, "review-approve")
  );
}

export async function rejectReviewItem(
  options: IdempotentApiClientOptions,
  reviewId: string,
  body: ReviewActionRequest = {},
): Promise<ReviewActionResponse> {
  return reviewActionResponseSchema.parse(
    await authenticatedIdempotentRequest(`/api/v1/review/items/${reviewId}/reject`, "POST", body, options, "review-reject")
  );
}

export async function requestReviewRegeneration(
  options: IdempotentApiClientOptions,
  reviewId: string,
  body: ReviewActionRequest = {},
): Promise<ReviewActionResponse> {
  return reviewActionResponseSchema.parse(
    await authenticatedIdempotentRequest(
      `/api/v1/review/items/${reviewId}/request-regeneration`,
      "POST",
      body,
      options,
      "review-request-regeneration",
    )
  );
}

export async function runSendGateDryRun(
  options: IdempotentApiClientOptions,
  body: SendGateDryRunRequest,
): Promise<SendGateDryRunResponse> {
  return sendGateDryRunResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/send-gate/dry-run", "POST", body, options, "send-gate-dry-run")
  );
}

export async function createSendIntent(
  options: IdempotentApiClientOptions,
  body: SendIntentRequest,
): Promise<SendIntentResponse> {
  return sendIntentResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/send-intents", "POST", body, options, "send-intents")
  );
}

export async function createFollowUpRule(
  options: IdempotentApiClientOptions,
  body: FollowUpRuleCreateRequest,
): Promise<FollowUpRuleActionResponse> {
  return followUpRuleActionResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/followups/rules", "POST", body, options, "followups-rules")
  );
}

export async function createFollowUpSchedule(
  options: IdempotentApiClientOptions,
  body: FollowUpScheduleCreateRequest,
): Promise<FollowUpScheduleActionResponse> {
  return followUpScheduleActionResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/followups/schedules", "POST", body, options, "followups-schedules")
  );
}

export async function mockRunFollowUpSchedule(
  options: IdempotentApiClientOptions,
  scheduleId: string,
): Promise<FollowUpScheduleActionResponse> {
  return followUpScheduleActionResponseSchema.parse(
    await authenticatedIdempotentRequest(
      `/api/v1/followups/schedules/${scheduleId}/mock-run`,
      "POST",
      undefined,
      options,
      "followups-schedules-mock-run",
    )
  );
}

export async function createSuppression(
  options: IdempotentApiClientOptions,
  body: SuppressionCreateRequest,
): Promise<SuppressionActionResponse> {
  return suppressionActionResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/suppressions", "POST", body, options, "suppressions-create")
  );
}

export async function reinstateSuppression(
  options: IdempotentApiClientOptions,
  suppressionId: string,
): Promise<SuppressionActionResponse> {
  return suppressionActionResponseSchema.parse(
    await authenticatedIdempotentRequest(
      `/api/v1/suppressions/${suppressionId}/reinstate`,
      "POST",
      undefined,
      options,
      "suppressions-reinstate",
    )
  );
}

export async function updateTenantSettings(
  options: IdempotentApiClientOptions,
  body: TenantUpdateRequest,
): Promise<TenantUpdateResponse> {
  return tenantUpdateResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/tenants/current", "PATCH", body, options, "tenants-current-update")
  );
}

export async function updateComplianceProfile(
  options: IdempotentApiClientOptions,
  body: ComplianceProfileUpdateRequest,
): Promise<ComplianceProfileActionResponse> {
  return complianceProfileActionResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/compliance/profile", "PUT", body, options, "compliance-profile-update")
  );
}

export async function createMockOutcomeEvent(
  options: IdempotentApiClientOptions,
  body: MockOutcomeEventRequest,
): Promise<MockOutcomeEventResponse> {
  return mockOutcomeEventResponseSchema.parse(
    await authenticatedIdempotentRequest("/api/v1/outcomes/mock-events", "POST", body, options, "outcomes-mock-events")
  );
}

export function formatZodError(error: z.ZodError): string {
  return error.issues.map((issue) => issue.message).join(", ");
}
