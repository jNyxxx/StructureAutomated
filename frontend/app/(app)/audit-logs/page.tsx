"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { AuditDetailDrawer } from "@/components/audit/audit-detail-drawer";
import { auditRows, type AuditRow, type AuditSeverity } from "@/components/audit/audit-sample-data";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { fetchAuditEvents } from "@/lib/backend-api";

function SeverityBadge({ severity }: { severity: AuditSeverity }) {
  if (severity === "critical") return <GateReasonBadge state="blocked" label="critical" />;
  if (severity === "blocked") return <GateReasonBadge state="blocked" label="blocked" />;
  if (severity === "warning") return <GateReasonBadge state="warning" label="warning" />;
  return <GateReasonBadge state="passed" label="info" />;
}

const columns: DataTableColumn<AuditRow>[] = [
  { id: "timestamp", header: "Timestamp", accessor: "timestamp", sortable: true },
  { id: "actor", header: "Actor", accessor: "actor", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.actor}</span> },
  { id: "role", header: "Role", accessor: "role", sortable: true },
  { id: "action", header: "Action", accessor: "action", sortable: true },
  { id: "resource", header: "Resource", accessor: "resource", sortable: true },
  { id: "severity", header: "Severity", accessor: "severity", sortable: true, cell: (row) => <SeverityBadge severity={row.severity} /> },
  { id: "requestId", header: "request_id", accessor: "requestId", sortable: true, cell: (row) => <span className="break-all text-caption">{row.requestId}</span> },
  { id: "correlationId", header: "correlation_id", accessor: "correlationId", sortable: true, cell: (row) => <span className="break-all text-caption">{row.correlationId}</span> },
];

export default function AuditLogsPage() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [rows, setRows] = useState<AuditRow[]>(auditRows);
  const [loading, setLoading] = useState(true);

  const loadAuditEvents = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setRows(auditRows);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetchAuditEvents({
        getToken: auth.getToken,
        getTenantId: () => selectedTenantId,
      });

      const mapped = res.audit_events.map((evt) => {
        let severity: AuditSeverity = "info";
        if (evt.event_type.includes("blocked") || evt.event_type.includes("denied")) {
          severity = "blocked";
        } else if (evt.event_type.includes("error") || evt.event_type.includes("failed")) {
          severity = "critical";
        } else if (evt.event_type.includes("warn") || evt.event_type.includes("grace")) {
          severity = "warning";
        }

        const isCurrentUser = auth.userId === evt.actor_user_id;
        const actor = isCurrentUser
          ? (auth.email ?? "owner@example.com")
          : (evt.actor_user_id ? `user:${evt.actor_user_id.slice(0, 8)}` : "system");
        const role = isCurrentUser ? "tenant_owner" : (evt.actor_user_id ? "member" : "system");

        const redactedDetails: Record<string, string> = {};
        if (evt.redacted_details) {
          Object.entries(evt.redacted_details).forEach(([key, val]) => {
            redactedDetails[key] = typeof val === "object" ? JSON.stringify(val) : String(val);
          });
        }

        return {
          id: evt.id,
          timestamp: new Date(evt.created_at).toLocaleString(),
          actor,
          role,
          action: evt.event_type,
          resource: evt.object_type ?? "unknown",
          severity,
          requestId: evt.request_id ?? "N/A",
          correlationId: "N/A",
          redactedDetails,
        };
      });
      setRows(mapped.length > 0 ? mapped : auditRows);
    } catch (err) {
      console.error("Failed to load audit events, falling back to mock logs:", err);
      setRows(auditRows);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadAuditEvents();
  }, [loadAuditEvents]);

  const savedViews: SavedViewTab[] = [
    { id: "all", label: "All audit events", count: rows.length },
    { id: "blocked", label: "Blocked/critical", count: rows.filter((r) => r.severity === "blocked" || r.severity === "critical").length },
    { id: "support", label: "Support access", count: rows.filter((r) => r.action.includes("support")).length },
    { id: "export", label: "Export API", count: 0, locked: true },
  ];

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Safe observability"
        title="Audit logs"
        description="Redacted audit logs fetched from backend. Secrets, tokens, raw contact identifiers, tenant IDs, and sessions are never rendered."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Export locked</Badge>
          </>
        }
      />
      <LocalMockNotice />
      <Card className="border-yellow/25 bg-warnbg/60">
        <CardHeader>
          <div className="flex gap-3">
            <div className="flex size-10 items-center justify-center rounded-medium bg-warnbg text-yellow">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <CardTitle>Audit API/export pending</CardTitle>
              <CardDescription>
                Export, raw detail fetch, and support-access enforcement are pending backend mutation APIs. Details are redacted in the UI.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <GateReasonBadge state="passed" label="Redaction visible" />
          {loading ? (
            <GateReasonBadge state="pending" label="Loading..." />
          ) : (
            <GateReasonBadge state="passed" label="Audit API wired" />
          )}
          <GateReasonBadge state="blocked" label="Export locked" />
          <GateReasonBadge state="warning" label="Support access audited" />
        </CardContent>
      </Card>
      <DataTable
        label="Audit log table"
        data={rows}
        columns={columns}
        filters={[
          { key: "scope", label: "Scope", value: loading ? "loading..." : "local/wired" },
          { key: "retention", label: "Retention", value: "accountability" },
        ]}
        savedViews={savedViews}
        rowActions={[
          { label: "Open redacted details" },
          { label: "Export audit logs", pendingBackend: true },
          { label: "Fetch raw JSON", pendingBackend: true },
          { label: "Delete event", disabled: true, pendingBackend: true },
        ]}
        getRowSearchText={(row) =>
          `${row.timestamp} ${row.actor} ${row.role} ${row.action} ${row.resource} ${row.severity} ${row.requestId} ${row.correlationId}`
        }
        getDrawerTitle={(row) => row.action}
        renderDrawer={(row) => <AuditDetailDrawer row={row} />}
      />
    </section>
  );
}
