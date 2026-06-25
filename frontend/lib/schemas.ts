import { z } from "zod";

/**
 * The backend standard error envelope:
 *   { "error": { "code", "message", "details", "request_id", "correlation_id" } }
 */
export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional().default({}),
    request_id: z.string().nullable().optional(),
    correlation_id: z.string().nullable().optional(),
  }),
});

export type ErrorEnvelope = z.infer<typeof errorEnvelopeSchema>;

export const principalSchema = z.object({
  provider_user_id: z.string(),
  user_id: z.string().uuid(),
  email: z.string().email(),
  tenant_id: z.string().uuid(),
  role: z.string(),
  membership_version: z.number().int(),
  mfa_verified: z.boolean(),
});

export const authMeResponseSchema = z.object({
  principal: principalSchema,
});

export type Principal = z.infer<typeof principalSchema>;
export type AuthMeResponse = z.infer<typeof authMeResponseSchema>;

export const healthResponseSchema = z
  .object({
    status: z.string().optional(),
    ok: z.boolean().optional(),
    service: z.string().optional(),
    version: z.string().optional(),
    checks: z.record(z.string(), z.unknown()).optional(),
    request_id: z.string().nullable().optional(),
    correlation_id: z.string().nullable().optional(),
  })
  .passthrough();

export type HealthResponse = z.infer<typeof healthResponseSchema>;

export const billingGateStatusSchema = z.object({
  tenant_id: z.string().uuid().nullable(),
  tenant_status: z.enum(["trialing", "active", "past_due", "canceled", "unpaid", "inactive", "unknown"]),
  mode: z.enum(["normal", "limited", "read_only", "locked", "loading", "error"]),
  is_active: z.boolean(),
  gates: z.object({
    can_send: z.boolean(),
    can_run_agents: z.boolean(),
    can_create_campaign: z.boolean(),
    can_export: z.boolean(),
  }),
  message: z.string(),
});

export type BillingGateStatus = z.infer<typeof billingGateStatusSchema>;

export const auditEventSchema = z.object({
  id: z.string().uuid(),
  event_type: z.string(),
  actor_user_id: z.string().uuid().nullable().optional(),
  object_type: z.string().nullable().optional(),
  object_id: z.string().uuid().nullable().optional(),
  request_id: z.string().nullable().optional(),
  job_id: z.string().uuid().nullable().optional(),
  redacted_details: z.record(z.string(), z.unknown()).default({}),
  created_at: z.string(),
});

export const auditLogResponseSchema = z.object({
  events: z.array(auditEventSchema),
});

export type AuditEvent = z.infer<typeof auditEventSchema>;
export type AuditLogResponse = z.infer<typeof auditLogResponseSchema>;

export const billingPlanSchema = z.object({
  key: z.string(),
  name: z.string(),
  features: z.record(z.string(), z.boolean()),
  mock_only: z.boolean().optional(),
});

export const billingSubscriptionSchema = z.object({
  plan: billingPlanSchema.nullable().optional(),
  tenant_status: z.string(),
  grace_until: z.string().nullable().optional(),
  mock_only: z.boolean().optional(),
});

export const billingSubscriptionResponseSchema = z.object({
  subscription: billingSubscriptionSchema,
  mock_only: z.boolean().optional(),
});

export const billingAccessSchema = z.object({
  is_active: z.boolean(),
  can_send: z.boolean(),
  can_run_agents: z.boolean(),
  can_create_campaign: z.boolean(),
  can_export: z.boolean(),
  mock_only: z.boolean().optional(),
});

export const billingAccessResponseSchema = z.object({
  access: billingAccessSchema,
  mock_only: z.boolean().optional(),
});

export const usageSnapshotSchema = z.object({
  contacts_total: z.number().int(),
  contact_imports_total: z.number().int(),
  campaigns_total: z.number().int(),
  drafts_total: z.number().int(),
  outbound_mock_sent: z.number().int(),
  outbound_blocked: z.number().int(),
  send_gate_denied: z.number().int(),
  followups_mock_sent: z.number().int(),
  followups_skipped: z.number().int(),
  research_runs_total: z.number().int(),
  outcome_events_total: z.number().int(),
  mock_only: z.boolean().optional(),
});

export const usageResponseSchema = z.object({
  usage: usageSnapshotSchema,
  mock_only: z.boolean().optional(),
});

export type BillingPlan = z.infer<typeof billingPlanSchema>;
export type BillingSubscription = z.infer<typeof billingSubscriptionSchema>;
export type BillingSubscriptionResponse = z.infer<typeof billingSubscriptionResponseSchema>;
export type BillingAccess = z.infer<typeof billingAccessSchema>;
export type BillingAccessResponse = z.infer<typeof billingAccessResponseSchema>;
export type UsageSnapshot = z.infer<typeof usageSnapshotSchema>;
export type UsageResponse = z.infer<typeof usageResponseSchema>;

// Settings & Current Tenant Settings
export const tenantSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  status: z.string(),
  settings: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  updated_at: z.string(),
  mock_only: z.boolean().optional(),
});

export const tenantResponseSchema = z.object({
  tenant: tenantSchema,
  mock_only: z.boolean().optional(),
});

export type Tenant = z.infer<typeof tenantSchema>;
export type TenantResponse = z.infer<typeof tenantResponseSchema>;

// Memberships (Team)
export const membershipSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  role: z.string(),
  membership_version: z.number().int(),
  created_at: z.string(),
  mock_only: z.boolean().optional(),
});

export const membershipListResponseSchema = z.object({
  memberships: z.array(membershipSchema),
  mock_only: z.boolean().optional(),
});

export type Membership = z.infer<typeof membershipSchema>;
export type MembershipListResponse = z.infer<typeof membershipListResponseSchema>;

// Audit Logs (with Pagination)
export const pageInfoSchema = z.object({
  next_cursor: z.string().nullable().optional(),
  limit: z.number().int(),
});

export const auditEventListResponseSchema = z.object({
  audit_events: z.array(auditEventSchema),
  page: pageInfoSchema,
  mock_only: z.boolean().optional(),
});

export type PageInfo = z.infer<typeof pageInfoSchema>;
export type AuditEventListResponse = z.infer<typeof auditEventListResponseSchema>;

// Compliance Profile
export const complianceProfileSchema = z.object({
  jurisdiction: z.string(),
  sending_review_required: z.boolean(),
  live_sending_allowed: z.boolean(),
  sms_allowed: z.boolean(),
  mock_only: z.boolean().optional(),
});

export const complianceProfileResponseSchema = z.object({
  compliance_profile: complianceProfileSchema,
  mock_only: z.boolean().optional(),
});

export type ComplianceProfile = z.infer<typeof complianceProfileSchema>;
export type ComplianceProfileResponse = z.infer<typeof complianceProfileResponseSchema>;

// Suppressions
export const suppressionSchema = z.object({
  id: z.string().uuid(),
  channel: z.string(),
  reason: z.string(),
  source: z.string(),
  never_contact: z.boolean(),
  created_at: z.string(),
  revoked_at: z.string().nullable().optional(),
  active: z.boolean(),
  mock_only: z.boolean().optional(),
});

export const suppressionListResponseSchema = z.object({
  suppressions: z.array(suppressionSchema),
  page: pageInfoSchema,
  mock_only: z.boolean().optional(),
});

export type Suppression = z.infer<typeof suppressionSchema>;
export type SuppressionListResponse = z.infer<typeof suppressionListResponseSchema>;

// Contacts / Prospects
export const contactSchema = z.object({
  id: z.string().uuid(),
  full_name: z.string().nullable().optional(),
  title: z.string().nullable().optional(),
  email: z.string().email().nullable().optional(),
  domain: z.string().nullable().optional(),
  company_name: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  mock_only: z.boolean().optional(),
});

export const prospectSchema = z.object({
  id: z.string().uuid(),
  contact_id: z.string().uuid(),
  full_name: z.string().nullable().optional(),
  title: z.string().nullable().optional(),
  email: z.string().email().nullable().optional(),
  domain: z.string().nullable().optional(),
  company_name: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  mock_only: z.boolean().optional(),
});

export const contactListResponseSchema = z.object({
  contacts: z.array(contactSchema),
  page: pageInfoSchema,
  mock_only: z.boolean().optional(),
});

export const prospectListResponseSchema = z.object({
  prospects: z.array(prospectSchema),
  page: pageInfoSchema,
  mock_only: z.boolean().optional(),
});

export const contactDetailResponseSchema = z.object({
  contact: contactSchema,
  mock_only: z.boolean().optional(),
});

export type Contact = z.infer<typeof contactSchema>;
export type Prospect = z.infer<typeof prospectSchema>;
export type ContactListResponse = z.infer<typeof contactListResponseSchema>;
export type ProspectListResponse = z.infer<typeof prospectListResponseSchema>;
export type ContactDetailResponse = z.infer<typeof contactDetailResponseSchema>;
