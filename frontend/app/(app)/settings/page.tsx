import Link from "next/link";
import { Building2, Lock, PlugZap, ShieldCheck, Users } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { PageHeader } from "@/components/layout/page-header";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const links = [
  { href: "/settings/team", label: "Team and roles", icon: Users, note: "Manage team members and roles" },
  { href: "/settings/integrations", label: "Integrations", icon: PlugZap, note: "Integrate external services" },
  { href: "/settings/security", label: "Security", icon: ShieldCheck, note: "Configure security credentials" },
  { href: "/settings/compliance", label: "Compliance", icon: ShieldCheck, note: "Manage legal and compliance rules" },
  { href: "/settings/suppression", label: "Suppression", icon: Lock, note: "Manage contact suppression rules" },
];

export default function SettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Tenant settings" title="Settings" description="Configure tenant workspace settings and legal name."  />
      
      <BentoCard title="Tenant profile" description="Manage tenant workspace profile and configuration." badge="Active">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3"><div className="flex items-center gap-2 text-small font-semibold text-text"><Building2 className="size-4 text-blue" /> Tenant</div><p className="mt-2 text-small text-muted">Automated Structure Demo Tenant</p></div>
          <div className="rounded-medium border border-border bg-panel2 p-3"><p className="text-small font-semibold text-text">Workspace mode</p><p className="mt-2 text-small text-muted">Production active</p></div>
          <div className="rounded-medium border border-border bg-panel2 p-3"><p className="text-small font-semibold text-text">Save status</p><GateReasonBadge state="passed" label="Operational" className="mt-2" /></div>
        </div>
        <div className="mt-4"><Button>Save settings</Button></div>
      </BentoCard>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {links.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className="rounded-xl border border-border bg-panel p-5 shadow-panel transition hover:border-blue/50">
              <div className="flex items-start gap-3">
                <div className="flex size-10 items-center justify-center rounded-medium bg-bluebg text-blue"><Icon className="size-5" /></div>
                <div><p className="font-semibold text-text">{item.label}</p><p className="mt-1 text-small text-muted">{item.note}</p></div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
