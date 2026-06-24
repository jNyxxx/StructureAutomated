"use client";

import { Lock, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { teamMembers, type TeamMemberRow } from "./settings-sample-data";

function RoleBadge({ role }: { role: TeamMemberRow["role"] }) {
  return <Badge variant="outline">{role}</Badge>;
}

function MfaBadge({ status }: { status: TeamMemberRow["mfaStatus"] }) {
  return <GateReasonBadge state={status === "enabled" ? "passed" : status === "required" ? "warning" : "pending"} label={status} />;
}

const columns: DataTableColumn<TeamMemberRow>[] = [
  { id: "name", header: "Name", accessor: "name", sortable: true, cell: (row) => <span className="font-semibold text-text">{row.name}</span> },
  { id: "email", header: "Email", accessor: "email", sortable: true },
  { id: "role", header: "Role", accessor: "role", sortable: true, cell: (row) => <RoleBadge role={row.role} /> },
  { id: "mfaStatus", header: "MFA", accessor: "mfaStatus", sortable: true, cell: (row) => <MfaBadge status={row.mfaStatus} /> },
  { id: "status", header: "Status", accessor: "status", sortable: true, cell: (row) => <GateReasonBadge state={row.status === "active" ? "passed" : row.status === "invited" ? "pending" : "blocked"} label={row.status} /> },
  { id: "updatedAt", header: "Updated", accessor: "updatedAt", sortable: true },
];

const views: SavedViewTab[] = [
  { id: "all", label: "All members", count: teamMembers.length },
  { id: "admins", label: "Admins", count: 2 },
  { id: "mfa", label: "MFA required", count: 1 },
  { id: "invite", label: "Invite API", count: 0, locked: true },
];

export function TeamTable() {
  return (
    <DataTable
      label="Team members demo table"
      data={teamMembers}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[{ key: "runtime", label: "Runtime", value: "local/demo" }]}
      rowActions={[
        { label: "Invite member", pendingBackend: true },
        { label: "Change role", pendingBackend: true },
        { label: "Remove member", pendingBackend: true },
        { label: "Require MFA", pendingBackend: true },
      ]}
      getRowSearchText={(row) => `${row.name} ${row.email} ${row.role} ${row.mfaStatus} ${row.status}`}
      getDrawerTitle={(row) => row.name}
      renderDrawer={(row) => (
        <div className="space-y-3 text-small text-muted">
          <p>Read-only team member shell. Invite/remove/change-role actions require backend APIs.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-medium border border-border bg-panel2 p-3"><p className="font-semibold text-text">Role</p><RoleBadge role={row.role} /></div>
            <div className="rounded-medium border border-border bg-panel2 p-3"><p className="font-semibold text-text">MFA</p><MfaBadge status={row.mfaStatus} /></div>
          </div>
          <div className="flex flex-wrap gap-2"><Button disabled><Lock className="size-4" /> Mutations locked</Button><Button disabled variant="secondary"><ShieldCheck className="size-4" /> MFA action pending</Button></div>
        </div>
      )}
    />
  );
}
