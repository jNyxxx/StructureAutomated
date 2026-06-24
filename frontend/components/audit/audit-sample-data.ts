export type AuditSeverity = "info" | "warning" | "blocked" | "critical";

export interface AuditRow {
  id: string;
  timestamp: string;
  actor: string;
  role: string;
  action: string;
  resource: string;
  severity: AuditSeverity;
  requestId: string;
  correlationId: string;
  redactedDetails: Record<string, string>;
}

export const auditRows: AuditRow[] = [
  {
    id: "audit_demo_001",
    timestamp: "local demo",
    actor: "redacted:user:owner",
    role: "tenant_owner",
    action: "tenant.access_checked",
    resource: "tenant",
    severity: "info",
    requestId: "req_demo_tenant_001",
    correlationId: "corr_demo_tenant_001",
    redactedDetails: { scope: "tenant:read", result: "allowed", token: "[REDACTED]", email: "[REDACTED]" },
  },
  {
    id: "audit_demo_002",
    timestamp: "local demo",
    actor: "redacted:system",
    role: "system",
    action: "send_gate.blocked",
    resource: "mock_send",
    severity: "blocked",
    requestId: "req_demo_send_gate_002",
    correlationId: "corr_demo_send_gate_002",
    redactedDetails: { reason: "production_not_approved", contact_hash: "hash_demo_only", api_key: "[REDACTED]" },
  },
  {
    id: "audit_demo_003",
    timestamp: "local demo",
    actor: "redacted:user:reviewer",
    role: "tenant_admin",
    action: "review.queue_opened",
    resource: "review_queue",
    severity: "warning",
    requestId: "req_demo_review_003",
    correlationId: "corr_demo_review_003",
    redactedDetails: { state: "pending_backend_api", draft_id: "draft_demo_001", secret: "[REDACTED]" },
  },
  {
    id: "audit_demo_004",
    timestamp: "local demo",
    actor: "redacted:support",
    role: "platform_admin",
    action: "support.access_previewed",
    resource: "tenant_support_shell",
    severity: "critical",
    requestId: "req_demo_support_004",
    correlationId: "corr_demo_support_004",
    redactedDetails: { support_reason: "demo_review", tenant_id: "[REDACTED]", session: "[REDACTED]" },
  },
];
