import { AlertTriangle, UserPlus } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { TeamTable } from "@/components/settings/team-table";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function TeamSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="RBAC and team" title="Team settings" description="Team member and role shell for platform_admin, tenant_owner, tenant_admin, member, and viewer roles." actions={<><Badge variant="default">Local/mock MVP</Badge><Button disabled><UserPlus className="size-4" /> Invite locked</Button></>} />
      <LocalMockNotice />
      <Card className="border-yellow/25 bg-warnbg/60"><CardHeader><div className="flex gap-3"><div className="flex size-10 items-center justify-center rounded-medium bg-warnbg text-yellow"><AlertTriangle className="size-5" /></div><div><CardTitle>Team APIs pending</CardTitle><CardDescription>Invite, remove, change-role, and MFA actions are locked until backend routes exist.</CardDescription></div></div></CardHeader><CardContent className="flex flex-wrap gap-2"><GateReasonBadge state="pending" label="RBAC API pending" /><GateReasonBadge state="warning" label="MFA shell" /></CardContent></Card>
      <TeamTable />
    </section>
  );
}
