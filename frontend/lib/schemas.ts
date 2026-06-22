import { z } from "zod";

/**
 * The backend standard error envelope:
 *   { "error": { "code", "message", "details", "request_id" } }
 */
export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional().default({}),
    request_id: z.string().nullable().optional(),
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
