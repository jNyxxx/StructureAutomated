import {
  Activity,
  BarChart3,
  CreditCard,
  Database,
  FileText,
  Inbox,
  KeyRound,
  LayoutDashboard,
  Lock,
  Mail,
  Plug,
  ScrollText,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavStatus = "available" | "demo" | "pending-backend" | "locked";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  status: NavStatus;
  description: string;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

export const appNavSections: NavSection[] = [
  {
    label: "Command",
    items: [
      {
        label: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        status: "demo",
        description: "Local command center shell; deeper metrics come later.",
      },
      {
        label: "Prospects",
        href: "/prospects",
        icon: Users,
        status: "pending-backend",
        description: "Prospect list UI awaits contacts/prospects HTTP routes.",
      },
      {
        label: "Import CSV",
        href: "/prospects/import",
        icon: Upload,
        status: "pending-backend",
        description: "CSV import wizard shell only until import routes are mounted.",
      },
    ],
  },
  {
    label: "Outreach flow",
    items: [
      {
        label: "Campaigns",
        href: "/campaigns",
        icon: Send,
        status: "pending-backend",
        description: "Campaign actions stay locked until campaign APIs are mounted.",
      },
      {
        label: "Review Queue",
        href: "/review-queue",
        icon: Inbox,
        status: "pending-backend",
        description: "Human approval shell; backend gates remain source of truth.",
      },
      {
        label: "AI Drafts",
        href: "/ai-drafts",
        icon: Sparkles,
        status: "pending-backend",
        description: "Draft review shell; no auto-send or gate bypass.",
      },
      {
        label: "Deliverability",
        href: "/deliverability",
        icon: Activity,
        status: "pending-backend",
        description: "Mailbox health shell; no real sending or provider actions.",
      },
      {
        label: "Outcomes",
        href: "/outcomes",
        icon: BarChart3,
        status: "pending-backend",
        description: "ROI/outcomes shell awaiting mounted HTTP APIs.",
      },
    ],
  },
  {
    label: "Access & settings",
    items: [
      {
        label: "Billing",
        href: "/billing",
        icon: CreditCard,
        status: "demo",
        description: "Mock/read-only billing status; no real Stripe.",
      },
      {
        label: "Settings",
        href: "/settings",
        icon: Settings,
        status: "demo",
        description: "Workspace settings shell.",
      },
      {
        label: "Team",
        href: "/settings/team",
        icon: Users,
        status: "pending-backend",
        description: "Team/RBAC shell awaiting membership routes.",
      },
      {
        label: "Integrations",
        href: "/settings/integrations",
        icon: Plug,
        status: "pending-backend",
        description: "Integration credentials shell only.",
      },
      {
        label: "Security",
        href: "/settings/security",
        icon: ShieldCheck,
        status: "pending-backend",
        description: "Security/MFA shell; auth provider remains boundary.",
      },
      {
        label: "Compliance",
        href: "/settings/compliance",
        icon: Mail,
        status: "pending-backend",
        description: "Compliance profile shell awaiting APIs.",
      },
      {
        label: "Suppression",
        href: "/settings/suppression",
        icon: Database,
        status: "pending-backend",
        description: "Suppression shell; no outbound actions.",
      },
      {
        label: "Privacy",
        href: "/privacy",
        icon: KeyRound,
        status: "pending-backend",
        description: "Privacy export/delete shell awaiting APIs.",
      },
      {
        label: "Audit Logs",
        href: "/audit-logs",
        icon: ScrollText,
        status: "demo",
        description: "Redacted audit shell with safe fields only.",
      },
    ],
  },
];

export const flatAppNavItems = appNavSections.flatMap((section) => section.items);

export function getNavStatusLabel(status: NavStatus): string {
  if (status === "available") return "Live";
  if (status === "demo") return "Local demo";
  if (status === "pending-backend") return "Pending API";
  return "Locked";
}

export function getNavStatusIcon(status: NavStatus): LucideIcon {
  return status === "pending-backend" || status === "locked" ? Lock : FileText;
}

export function isActiveRoute(pathname: string, href: string): boolean {
  const exactOnlyRoutes = new Set(["/dashboard", "/prospects", "/settings"]);
  if (exactOnlyRoutes.has(href)) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}
