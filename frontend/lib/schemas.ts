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
