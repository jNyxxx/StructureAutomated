import type { AuditEvent } from "@/lib/schemas";

const SAFE_DETAIL_KEYS = new Set(["event", "status", "scope", "tenant_status", "grace"]);

export function AuditLogTable({
  events,
  state = "ready",
}: {
  events: AuditEvent[];
  state?: "loading" | "ready" | "empty" | "error" | "denied";
}) {
  if (state === "loading") {
    return <StateCard title="Loading audit logs" body="Fetching safe audit fields…" />;
  }
  if (state === "error") {
    return <StateCard title="Audit logs unavailable" body="The view failed safely without exposing raw error details." />;
  }
  if (state === "denied") {
    return <StateCard title="Access denied" body="You do not have permission to view audit logs for this tenant." />;
  }
  if (state === "empty" || events.length === 0) {
    return <StateCard title="No audit events yet" body="Security and access events will appear here after backend confirmation." />;
  }

  return (
    <div className="overflow-hidden rounded-lg border">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
          <tr>
            <th className="p-3">Time</th>
            <th className="p-3">Event</th>
            <th className="p-3">Actor</th>
            <th className="p-3">Object</th>
            <th className="p-3">Request</th>
            <th className="p-3">Safe details</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id} className="border-t align-top">
              <td className="p-3">{event.created_at}</td>
              <td className="p-3 font-medium">{event.event_type}</td>
              <td className="p-3">{event.actor_user_id ?? "system"}</td>
              <td className="p-3">{event.object_type ?? "—"}</td>
              <td className="p-3">{event.request_id ?? "—"}</td>
              <td className="p-3">{formatSafeDetails(event.redacted_details)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function formatSafeDetails(details: Record<string, unknown>): string {
  const safeEntries = Object.entries(details).filter(([key]) => SAFE_DETAIL_KEYS.has(key));
  if (safeEntries.length === 0) return "—";
  return safeEntries.map(([key, value]) => `${key}: ${String(value)}`).join(", ");
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-6 text-sm text-slate-700">
      <p className="font-medium text-slate-900">{title}</p>
      <p className="mt-1">{body}</p>
    </div>
  );
}
