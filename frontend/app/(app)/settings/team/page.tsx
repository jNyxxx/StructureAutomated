import { AlertTriangle, UserPlus } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { PageHeader } from "@/components/layout/page-header";
import { TeamTable } from "@/components/settings/team-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function TeamSettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="RBAC and team" title="Team settings" description="Manage team member roles and permissions." actions={<Button disabled><UserPlus className="size-4" /> Invite locked</Button>} />

      <TeamTable />
    </section>
  );
}
