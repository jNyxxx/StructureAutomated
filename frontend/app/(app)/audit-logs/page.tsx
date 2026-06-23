"use client";

import { ShieldCheck } from "lucide-react";

import { GateReasonBadge, StatusBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";

interface AuditDemoRow {
  id: string;
  eventType: string;
  actor: string;
  object: string;
  requestId: string;
  status: "approved" | "blocked" | "pending_review";
  createdAt: string;
  safeDetails: string;
}

const auditRows: AuditDemoRow[] = [
  {
    id: "audit_demo_001",
    eventType: "tenant.access_checked",
    actor: "redacted:user",
    object: "tenant",
    requestId: "req_demo_tenant",
    status: "approved",
    createdAt: "local demo",
    safeDetails: "scope: tenant:read",
  },
  {
    id: "audit_demo_002",
    eventType: "send_gate.blocked",
    actor: "redacted:system",
    object: "mock_send",
    requestId: "req_demo_send_gate",
    status: "blocked",
    createdAt: "local demo",
    safeDetails: "reason: production_not_approved",
  },
  {
    id: "audit_demo_003",
    eventType: "review.queue_opened",
    actor: "redacted:user",
    object: "review_queue",
    requestId: "req_demo_review",
    status: "pending_review",
    createdAt: "local demo",
    safeDetails: "state: pending_backend_api",
  },
];

const columns: DataTableColumn<AuditDemoRow>[] = [
  {
    id: "eventType",
    header: "Event",
    accessor: "eventType",
    sortable: true,
    cell: (row) => <span className="font-semibold text-text">{row.eventType}</span>,
  },
  { id: "actor", header: "Actor", accessor: "actor", sortable: true },
  { id: "object", header: "Object", accessor: "object", sortable: true },
  {
    id: "status",
    header: "Status",
    accessor: "status",
    sortable: true,
    cell: (row) => <StatusBadge status={row.status} />,
  },
  { id: "requestId", header: "Request ID", accessor: "requestId", sortable: true },
  { id: "createdAt", header: "Created", accessor: "createdAt", sortable: true },
];

const savedViews: SavedViewTab[] = [
  { id: "all", label: "All", count: auditRows.length },
  { id: "blocked", label: "Blocked", count: 1 },
  { id: "pending", label: "Pending backend", count: 1, locked: true },
];

export default function AuditLogsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Safe observability"
        title="Audit logs"
        description="Shared DataTable demo with redacted local rows only. Raw secrets, tokens, contact identifiers, and PII are not rendered."
      />
      <LocalMockNotice />
      <DataTable
        label="Audit log demo table"
        data={auditRows}
        columns={columns}
        filters={[{ key: "scope", label: "Scope", value: "redacted demo" }]}
        savedViews={savedViews}
        rowActions={[
          { label: "Open details", pendingBackend: true },
          { label: "Export event", pendingBackend: true },
          { label: "Delete event", disabled: true, pendingBackend: true },
        ]}
        getRowSearchText={(row) => `${row.eventType} ${row.actor} ${row.object} ${row.requestId} ${row.safeDetails}`}
        getDrawerTitle={(row) => row.eventType}
        renderDrawer={(row) => (
          <div className="space-y-4 text-small text-muted">
            <div className="flex items-center gap-2 rounded-medium border border-green/25 bg-goodbg p-3">
              <ShieldCheck className="size-4 text-green" /> Redacted local/demo row only.
            </div>
            <dl className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-medium border border-border bg-panel2 p-3">
                <dt className="font-semibold text-text">Request ID</dt>
                <dd className="break-all">{row.requestId}</dd>
              </div>
              <div className="rounded-medium border border-border bg-panel2 p-3">
                <dt className="font-semibold text-text">Safe details</dt>
                <dd>{row.safeDetails}</dd>
              </div>
            </dl>
            <GateReasonBadge state="pending" label="Detail API pending" />
          </div>
        )}
      />
    </section>
  );
}
