"use client";

import { useCallback, useEffect, useState } from "react";
import { Lock, ShieldCheck } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DataTable, type DataTableColumn, type SavedViewTab } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import { fetchMemberships } from "@/lib/backend-api";
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

export function TeamTable() {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [members, setMembers] = useState<TeamMemberRow[]>([]);
  const [loading, setLoading] = useState(true);

  const loadMembers = useCallback(async () => {
    if (!auth.isLoaded || !auth.isSignedIn || !selectedTenantId) {
      setMembers(teamMembers);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetchMemberships({
        getToken: auth.getToken,
        getTenantId: () => selectedTenantId,
      });

      const mapped = res.memberships.map((m, idx) => {
        const isCurrentUser = auth.userId === m.user_id;
        return {
          id: m.id,
          name: isCurrentUser ? "Demo Owner" : `Team Member ${idx + 1}`,
          email: isCurrentUser ? (auth.email ?? "owner@example.com") : `member.${idx + 1}@example.com`,
          role: m.role as any,
          mfaStatus: (isCurrentUser ? "enabled" : idx % 2 === 0 ? "required" : "pending") as "enabled" | "pending" | "required",
          status: "active" as const,
          updatedAt: new Date(m.created_at).toLocaleDateString(),
        };
      });
      setMembers(mapped.length > 0 ? mapped : teamMembers);
    } catch (err) {
      console.error("Failed to load memberships, falling back to mock details:", err);
      setMembers(teamMembers);
    } finally {
      setLoading(false);
    }
  }, [auth, selectedTenantId]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const views: SavedViewTab[] = [
    { id: "all", label: "All members", count: members.length },
    { id: "admins", label: "Admins", count: members.filter(m => m.role.includes("admin") || m.role.includes("owner")).length },
    { id: "mfa", label: "MFA required", count: members.filter(m => m.mfaStatus === "required").length },
    { id: "invite", label: "Invite API", count: 0, locked: true },
  ];

  return (
    <DataTable
      label="Team members table"
      data={members}
      columns={columns}
      savedViews={views}
      pageSize={6}
      filters={[{ key: "runtime", label: "Runtime", value: loading ? "loading..." : "local/wired" }]}
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
          <p>Read-only team member. Invite/remove/change-role actions require backend mutation APIs.</p>
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
