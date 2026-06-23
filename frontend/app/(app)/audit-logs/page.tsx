import { AuditLogTable } from "@/components/audit-log-table";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/states";
import type { AuditEvent } from "@/lib/schemas";

const sampleEvents: AuditEvent[] = [];

export default function AuditLogsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Safe observability"
        title="Audit logs"
        description="Safe audit fields only. Raw secrets, tokens, contact identifiers, and PII are not rendered."
      />
      <EmptyState
        title="Audit timeline empty"
        description="Security and access events will appear here after backend confirmation."
      />
      <AuditLogTable events={sampleEvents} state="empty" />
    </section>
  );
}
