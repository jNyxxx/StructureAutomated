import Link from "next/link";
import { Building2, Lock, PlugZap, ShieldCheck, Users } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { PageHeader } from "@/components/layout/page-header";
import { LocalMockNotice } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const links = [
  { href: "/settings/team", label: "Team and roles", icon: Users, note: "RBAC/MFA shell" },
  { href: "/settings/integrations", label: "Integrations", icon: PlugZap, note: "Provider cards locked" },
  { href: "/settings/security", label: "Security", icon: ShieldCheck, note: "Auth/session shell" },
  { href: "/settings/compliance", label: "Compliance", icon: ShieldCheck, note: "US-first baseline" },
  { href: "/settings/suppression", label: "Suppression", icon: Lock, note: "No-send list shell" },
];

export default function SettingsPage() {
  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Tenant settings" title="Settings" description="Tenant profile/settings shell. Backend mutation APIs and provider integrations are not mounted." actions={<><Badge variant="default">Local/mock MVP</Badge><Badge variant="locked">Production not approved</Badge></>} />
      <LocalMockNotice />
      <BentoCard title="Tenant profile shell" description="Read-only tenant settings preview. Save actions are locked until backend APIs exist." badge="Settings shell">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3"><div className="flex items-center gap-2 text-small font-semibold text-text"><Building2 className="size-4 text-blue" /> Tenant</div><p className="mt-2 text-small text-muted">Automated Structure Demo Tenant</p></div>
          <div className="rounded-medium border border-border bg-panel2 p-3"><p className="text-small font-semibold text-text">Workspace mode</p><p className="mt-2 text-small text-muted">local/mock only</p></div>
          <div className="rounded-medium border border-border bg-panel2 p-3"><p className="text-small font-semibold text-text">Save status</p><GateReasonBadge state="pending" label="Settings API pending" className="mt-2" /></div>
        </div>
        <div className="mt-4"><Button disabled><Lock className="size-4" /> Save settings locked</Button></div>
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
