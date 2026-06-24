export const privacyPosture = [
  { label: "Data isolation", state: "warning" as const, note: "Tenant isolation must be enforced by backend RLS and auth gates." },
  { label: "Retention", state: "pending" as const, note: "Soft delete first, then hard delete after 30 days." },
  { label: "Suppression minimal data", state: "passed" as const, note: "Suppression rows should keep only minimal hashed identifiers where possible." },
  { label: "Vector purge", state: "pending" as const, note: "Knowledge/vector purge APIs are pending backend wiring." },
];

export const retentionItems = [
  { label: "Contacts", detail: "Soft delete on request; hard delete after 30 days where legally allowed." },
  { label: "Prospect research", detail: "Delete/purge workflow must also remove derived artifacts and embeddings." },
  { label: "Suppression", detail: "Minimal hashed suppression data may remain to prevent future no-send violations." },
  { label: "Audit events", detail: "Retained for accountability with secrets and PII redacted from UI." },
];

export const privacyTimeline = [
  { label: "Request received", state: "passed" as const, detail: "Local/demo request shell created." },
  { label: "Identity verification", state: "pending" as const, detail: "Backend verification workflow pending." },
  { label: "Export/delete processing", state: "pending" as const, detail: "Export, delete, vector purge, and confirmation APIs pending." },
  { label: "Completion", state: "blocked" as const, detail: "No fake completion is shown without backend evidence." },
];
