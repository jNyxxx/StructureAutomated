"use client";

import { AlertTriangle } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { AuditDetailDrawer } from "@/components/audit/audit-detail-drawer";
import { auditRows, type AuditRow, type AuditSeverity } from "@/components/audit/audit-sample-data";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { PageHeader } from "@/components/layout/page-header";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

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

const savedViews: SavedViewTab[] = [
  { id: "all", label: "All audit events", count: auditRows.length },
  { id: "blocked", label: "Blocked/critical", count: 2 },
  { id: "support", label: "Support access", count: 1 },
  { id: "export", label: "Export API", count: 0, locked: true },
];

export default function AuditLogsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Safe observability"
        title="Audit logs"
        description="Immutable history of system access and sensitive operations."
        
      />

      <DataTable
        label="Audit log demo table"
        data={auditRows}
        columns={columns}
        filters={[{ key: "scope", label: "Scope", value: "redacted demo" }, { key: "retention", label: "Retention", value: "accountability" }]}
        savedViews={savedViews}
        rowActions={[
          { label: "Open redacted details" },
          { label: "Export audit logs", pendingBackend: true },
          { label: "Fetch raw JSON", pendingBackend: true },
          { label: "Delete event", disabled: true, pendingBackend: true },
        ]}
        getRowSearchText={(row) => `${row.timestamp} ${row.actor} ${row.role} ${row.action} ${row.resource} ${row.severity} ${row.requestId} ${row.correlationId}`}
        getDrawerTitle={(row) => row.action}
        renderDrawer={(row) => <AuditDetailDrawer row={row} />}
      />
    </section>
  );
}
