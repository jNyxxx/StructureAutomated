"use client";

import Link from "next/link";
import { KeyRound, Lock, MailCheck, RotateCcw, ShieldCheck, UserPlus } from "lucide-react";

import { AuthSecurityPanel } from "@/components/public/auth-security-panel";
import { DemoStatusPill } from "@/components/public/demo-status-pill";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useFrontendAuth } from "@/lib/clerk";

export type AuthCardMode = "login" | "signup" | "verify-email" | "forgot-password" | "reset-password";

const copy: Record<AuthCardMode, { title: string; body: string; action: string; icon: typeof KeyRound; pending?: boolean }> = {
  login: {
    title: "Sign in",
    body: "Access the local/mock command center through the Clerk-owned auth boundary.",
    action: "Official Clerk sign-in mount",
    icon: KeyRound,
  },
  signup: {
    title: "Create account",
    body: "Account creation is delegated to Clerk. The app never stores credentials.",
    action: "Official Clerk sign-up mount",
    icon: UserPlus,
  },
  "verify-email": {
    title: "Verify your email",
    body: "Email verification is handled by Clerk before backend tenant access is granted.",
    action: "Official Clerk verification flow",
    icon: MailCheck,
  },
  "forgot-password": {
    title: "Forgot access",
    body: "Account recovery belongs to the auth provider. This route is a safe visual shell until the provider mount is wired.",
    action: "Pending Clerk recovery mount",
    icon: RotateCcw,
    pending: true,
  },
  "reset-password": {
    title: "Reset access",
    body: "Reset flow is not handled by the app backend. This shell waits for the provider reset flow.",
    action: "Pending Clerk reset flow mount",
    icon: Lock,
    pending: true,
  },
};

export function AuthCard({ mode }: { mode: AuthCardMode }) {
  const item = copy[mode];
  const Icon = item.icon;
  const auth = useFrontendAuth();
  const showDemoLogin = mode === "login" && auth.mode === "local_mock" && typeof auth.mockSignIn === "function";

  return (
    <main className="min-h-screen bg-bg text-text">
      <div className="mx-auto grid min-h-screen max-w-7xl items-center gap-8 px-6 py-10 lg:grid-cols-[0.95fr_1.05fr] lg:px-8">
        <section className="space-y-6">
          <Link href="/" className="inline-flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-medium bg-bluebg text-blue">
              <ShieldCheck className="size-5" />
            </div>
            <div>
              <p className="text-small font-bold">Automated Structure</p>
              <p className="text-caption text-muted">Secure marketing command center</p>
            </div>
          </Link>
          <div>
            <DemoStatusPill />
            <h1 className="mt-6 max-w-xl text-h1">Secure access for a gated automation workspace.</h1>
            <p className="mt-4 max-w-xl text-body text-muted">
              Auth pages match the v4 command-center style while preserving the local/mock Clerk boundary and fail-closed production behavior.
            </p>
          </div>
          <AuthSecurityPanel />
        </section>

        <Card className="mx-auto w-full max-w-lg border-blue/20 bg-panel/95 shadow-glow">
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div className="flex size-12 items-center justify-center rounded-large bg-bluebg text-blue">
                <Icon className="size-6" />
              </div>
              <Badge variant={item.pending ? "warning" : "default"}>{item.pending ? "Provider pending" : "Clerk shell"}</Badge>
            </div>
            <h2 className="mt-5 text-h3 text-text">{item.title}</h2>
            <CardDescription>{item.body}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-large border border-dashed border-border bg-panel2 p-4 text-small text-muted">
              <p className="font-semibold text-text">{item.action}</p>
              <p className="mt-2">
                This is the frontend mount point. Unsupported flows stay pending provider wiring and no production JWT work is added here.
              </p>
            </div>

            <div className="space-y-3" aria-hidden="true">
              <Input placeholder="email@example.com" disabled />
              {mode !== "verify-email" ? <Input placeholder="Auth provider field" disabled /> : null}
            </div>

            <Button className="w-full" disabled={item.pending}>
              {item.pending ? "Pending auth provider" : item.title}
            </Button>

            {showDemoLogin ? (
              <div className="space-y-3">
                <div className="relative flex items-center">
                  <div className="flex-grow border-t border-border" />
                  <span className="mx-3 shrink text-caption text-muted">or</span>
                  <div className="flex-grow border-t border-border" />
                </div>
                <Button
                  className="w-full"
                  variant="secondary"
                  onClick={() => {
                    auth.mockSignIn?.();
                    window.location.href = "/dashboard";
                  }}
                >
                  Continue with Demo Account
                </Button>
                <p className="text-center text-caption text-muted">Local/mock mode · No real credentials required</p>
              </div>
            ) : null}

            <div className="flex flex-wrap justify-between gap-3 text-small text-muted">
              <Link href="/login" className="hover:text-text">Sign in</Link>
              <Link href="/signup" className="hover:text-text">Create account</Link>
              <Link href="/forgot-password" className="hover:text-text">Forgot access</Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
