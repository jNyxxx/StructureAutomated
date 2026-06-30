import Link from "next/link";
import {
  BarChart3,
  CheckCircle2,
  Database,
  FileText,
  Lock,
  MailCheck,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
} from "lucide-react";

import { DemoStatusPill } from "@/components/public/demo-status-pill";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const flow = [
  { icon: Upload, title: "Import prospects", text: "Start from CSV intake with automatic validation before campaign work begins." },
  { icon: Send, title: "Create campaign", text: "Define a CRE-focused outreach motion with custom target segments." },
  { icon: Search, title: "Research + RAG", text: "Ground drafting against verified company profiles and source snippets." },
  { icon: Sparkles, title: "Generate AI drafts", text: "Produce personalized copies verified against groundedness metrics." },
  { icon: ShieldCheck, title: "Safety validation", text: "Automatic prompt-injection checks, suppression lists, and compliance filters." },
  { icon: Users, title: "Human review queue", text: "Mandatory manual approval or revision request before scheduled sending." },
  { icon: MailCheck, title: "Send workflow", text: "Staged queue system with automated delivery tracking and status logs." },
  { icon: BarChart3, title: "Visibility & Outcomes", text: "Interactive deliverability statistics and outbound response analytics." },
];

const trust = [
  "Tenant isolation and backend-owned access decisions",
  "RBAC and membership version checks",
  "Central billing gates for costly/outbound actions",
  "Audit logs with redacted details and request IDs",
  "Suppression/compliance states before outreach",
  "Strict safety validations for automated workflows",
];

const features = [
  {
    title: "Built for high-ticket marketing operations",
    text: "A command-center experience for teams that need controlled prospecting, review, and outcome visibility.",
  },
  {
    title: "AI with guardrails, not blind automation",
    text: "Draft generation is paired with groundedness checks, source context, and human approval boundaries.",
  },
  {
    title: "Audit logging and analytics",
    text: "Comprehensive event logging, request correlation tracking, and outcomes performance analytics.",
  },
];

export function PublicLandingShell() {
  return (
    <main className="min-h-screen overflow-hidden bg-bg text-text">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.18),transparent_28rem),radial-gradient(circle_at_top_right,rgba(139,92,246,0.14),transparent_26rem)]" />
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-8">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-medium bg-bluebg text-blue">
            <Database className="size-5" />
          </div>
          <div>
            <p className="text-small font-bold">Automated Structure</p>
            <p className="text-caption text-muted">Marketing automation command center</p>
          </div>
        </Link>
        <nav className="hidden items-center gap-6 text-small text-muted md:flex" aria-label="Public navigation">
          <a href="#flow" className="hover:text-text">Flow</a>
          <a href="#security" className="hover:text-text">Security</a>
          <a href="#scope" className="hover:text-text">Sandbox</a>
        </nav>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" className="hidden sm:inline-flex">
            <Link href="/login">Sign in</Link>
          </Button>
          <Button asChild>
            <Link href="/login">Explore Sandbox</Link>
          </Button>
        </div>
      </header>

      <HeroSection />
      <ProductFlowSection />
      <FeatureGrid />
      <SecurityTrustSection />
      <CTASection />
    </main>
  );
}

function HeroSection() {
  return (
    <section className="mx-auto grid max-w-7xl gap-10 px-6 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:px-8 lg:py-24">
      <div>
        <DemoStatusPill />
        <h1 className="mt-8 max-w-4xl text-display text-text">
          High-ticket marketing automation with AI review gates and controlled outreach.
        </h1>
        <p className="mt-6 max-w-2xl text-body text-muted">
          Automated Structure brings prospect intake, campaign planning, research grounding, AI draft generation, human review, deliverability visibility, and outcome tracking into one integrated workflow.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/login">Sign in to Console</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/login">Explore Sandbox</Link>
          </Button>
        </div>
        <p className="mt-4 max-w-2xl text-small text-subtle">
          Secure tenant workspace. Connected to the sandbox environment.
        </p>
      </div>
      <Card className="relative overflow-hidden border-blue/20 bg-panel/90">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <Badge variant="default">Outreach Engine</Badge>
            <Badge variant="success">Compliance Verified</Badge>
          </div>
          <CardTitle className="mt-4">Sales outreach workflow</CardTitle>
          <CardDescription>
            Visual workflow preview of gated outreach and compliance gates.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {flow.slice(0, 6).map((item, index) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="group flex items-start gap-3 rounded-medium border border-border bg-panel2 p-3 transition-all duration-300">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-small bg-bluebg text-blue mt-0.5">
                  <Icon className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-small font-semibold text-text">{index + 1}. {item.title}</p>
                  <p className="truncate group-hover:whitespace-normal text-caption text-muted transition-all duration-300">{item.text}</p>
                </div>
                <CheckCircle2 className="size-4 shrink-0 text-green mt-1 opacity-80" />
              </div>
            );
          })}
        </CardContent>
      </Card>
    </section>
  );
}

function ProductFlowSection() {
  return (
    <section id="flow" className="mx-auto max-w-7xl px-6 py-12 lg:px-8">
      <div className="border-t border-border pt-12">
        <p className="text-caption font-semibold uppercase tracking-wider text-blue">Product Flow</p>
        <h2 className="mt-2 text-h1">From prospect import to reviewed outreach.</h2>
        <p className="mt-4 max-w-3xl text-body text-muted">
          Every prospect goes through standard data cleaning, AI draft personalization, automated brand guardrails check, and a mandatory human approval step.
        </p>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {flow.map((item, index) => {
            const Icon = item.icon;
            return (
              <Card key={item.title} className="bg-panel/70">
                <CardHeader className="pb-3">
                  <div className="flex size-10 items-center justify-center rounded-medium bg-bluebg text-blue">
                    <Icon className="size-5" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-caption font-semibold text-subtle">Step {index + 1}</p>
                  <CardTitle className="mt-1 text-medium">{item.title}</CardTitle>
                  <CardDescription className="mt-2">{item.text}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FeatureGrid() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-14 lg:px-8">
      <div className="grid gap-6 md:grid-cols-3">
        {features.map((feature) => (
          <Card key={feature.title} className="border-border/50 bg-panel/85">
            <CardHeader>
              <CardTitle className="text-large">{feature.title}</CardTitle>
              <CardDescription className="mt-2">{feature.text}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </section>
  );
}

function SecurityTrustSection() {
  return (
    <section id="security" className="mx-auto max-w-7xl px-6 py-14 lg:px-8">
      <Card className="bg-panel/95">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-12 items-center justify-center rounded-large bg-goodbg text-green">
              <ShieldCheck className="size-6" />
            </div>
            <div>
              <CardTitle>Security and trust boundaries</CardTitle>
              <CardDescription>
                Compliance safeguards, tenant isolation, and strict server-side validation.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {trust.map((item) => (
            <div key={item} className="flex gap-3 rounded-medium border border-border bg-panel2 p-3 text-small text-muted">
              <Lock className="mt-0.5 size-4 shrink-0 text-green" />
              <span>{item}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}

function CTASection() {
  return (
    <section id="scope" className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
      <div className="rounded-xl border border-blue/25 bg-bluebg/40 p-8 text-center shadow-glow">
        <DemoStatusPill className="mx-auto" />
        <h2 className="mx-auto mt-6 max-w-3xl text-h1">Explore the sandbox workspace.</h2>
        <p className="mx-auto mt-4 max-w-2xl text-body text-muted">
          Use the dashboard to inspect the current frontend foundation, tenant console, and compliance safety gates.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/login">Sign in to Console</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/login">Explore Sandbox</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
