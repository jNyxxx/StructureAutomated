import { AuditLogTable } from "@/components/audit-log-table";
import type { AuditEvent } from "@/lib/schemas";

const sampleEvents: AuditEvent[] = [];

export default function AuditLogsPage() {
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Audit logs</h1>
        <p className="mt-2 text-sm text-slate-600">
          Safe audit fields only. Raw secrets, tokens, contact identifiers, and PII are not rendered.
        </p>
      </div>
      <AuditLogTable events={sampleEvents} state="empty" />
    </section>
  );
}
