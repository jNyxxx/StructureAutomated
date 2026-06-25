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
  id: z.string(),
  event_type: z.string(),
  tenant_id: z.string().uuid().nullable(),
  actor_user_id: z.string().uuid().nullable(),
  object_type: z.string().nullable(),
  object_id: z.string().uuid().nullable(),
  request_id: z.string().nullable(),
  created_at: z.string(),
  redacted_details: z.record(z.string(), z.unknown()).default({}),
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


