"use client";

import { createContext, type ReactNode, useContext, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { LoadingState, LocalMockNotice, PermissionDeniedState } from "@/components/states";

export interface FrontendAuthState {
  isLoaded: boolean;
  isSignedIn: boolean;
  userId: string | null;
  email: string | null;
  getToken: () => Promise<string | null>;
  mode?: "real_clerk" | "local_mock";
}

const mockModeFlag = process.env.NEXT_PUBLIC_CLERK_MOCK_MODE;

export function isLocalMockAuthAllowed(
  nodeEnv: string | undefined = process.env.NODE_ENV,
  explicitMockMode: string | undefined = mockModeFlag,
): boolean {
  return nodeEnv !== "production" || explicitMockMode === "true" || explicitMockMode === "1";
}

function blockedMockState(): FrontendAuthState {
  return {
    isLoaded: true,
    isSignedIn: false,
    userId: null,
    email: null,
    mode: "local_mock",
    getToken: async () => null,
  };
}

const localMockState: FrontendAuthState = {
  isLoaded: true,
  isSignedIn: false,
  userId: null,
  email: null,
  mode: "local_mock",
  getToken: async () => null,
};

const ClerkContext = createContext<FrontendAuthState>(localMockState);

/**
 * Local/mock Clerk boundary. The real @clerk/nextjs provider is intentionally not
 * mounted unless that package/config is added later. This adapter never stores
 * passwords or raw tokens. In production, local/mock auth fails closed unless
 * NEXT_PUBLIC_CLERK_MOCK_MODE is explicitly enabled for a controlled demo.
 */
export function ClerkFrontendProvider({
  children,
  value,
}: {
  children: ReactNode;
  value?: FrontendAuthState;
}) {
  const state = useMemo(() => {
    if (value) return value;
    return isLocalMockAuthAllowed() ? localMockState : blockedMockState();
  }, [value]);
  return <ClerkContext.Provider value={state}>{children}</ClerkContext.Provider>;
}

export function useFrontendAuth(): FrontendAuthState {
  return useContext(ClerkContext);
}

function AuthShell({ children }: { children: ReactNode }) {
  return <main className="min-h-screen bg-bg p-6 text-text lg:p-page-desktop">{children}</main>;
}

function MockAuthProductionBlock() {
  return (
    <AuthShell>
      <PermissionDeniedState
        title="Production auth blocked"
        description="Local/mock Clerk auth cannot run silently in production. Configure the real Clerk provider before enabling protected app routes."
      />
    </AuthShell>
  );
}

export function AuthGate({ children }: { children: ReactNode }) {
  const auth = useFrontendAuth();

  if (auth.mode === "local_mock" && !isLocalMockAuthAllowed()) {
    return <MockAuthProductionBlock />;
  }

  if (!auth.isLoaded) {
    return (
      <AuthShell>
        <LoadingState title="Loading secure session" description="Checking the frontend auth shell before tenant data is rendered." />
      </AuthShell>
    );
  }

  if (!auth.isSignedIn) {
    return (
      <AuthShell>
        <div className="max-w-2xl space-y-4">
          <PermissionDeniedState
            title="Authentication required"
            description="App routes are protected. Sign in through Clerk before accessing tenant data. If /auth/me is unavailable, tenant data remains locked."
            primaryAction={
              <Button asChild>
                <a href="/login">Go to sign in</a>
              </Button>
            }
          />
          <LocalMockNotice />
        </div>
      </AuthShell>
    );
  }

  return <>{children}</>;
}

export function ClerkAuthCard({ mode }: { mode: "login" | "signup" | "verify-email" }) {
  if (!isLocalMockAuthAllowed()) {
    return <MockAuthProductionBlock />;
  }

  const copy = {
    login: {
      title: "Sign in",
      body: "Clerk owns login, sessions, password reset, email verification, and MFA support.",
      action: "Official Clerk sign-in mount",
    },
    signup: {
      title: "Create account",
      body: "Account creation is delegated to Clerk. The app never stores passwords.",
      action: "Official Clerk sign-up mount",
    },
    "verify-email": {
      title: "Verify your email",
      body: "Email verification is handled by Clerk before backend tenant access is granted.",
      action: "Official Clerk verification flow",
    },
  }[mode];

  return (
    <main className="min-h-screen bg-bg p-8 text-text">
      <section className="max-w-lg rounded-xl border border-border bg-panel p-card-padding shadow-panel">
        <p className="text-caption font-semibold uppercase tracking-wide text-subtle">
          Clerk auth — local/mock mount
        </p>
        <h1 className="mt-2 text-h3">{copy.title}</h1>
        <p className="mt-2 text-small text-muted">{copy.body}</p>
        <div className="mt-5 rounded-medium border border-dashed border-border bg-panel2 p-4 text-small text-muted">
          {copy.action} plugs in here when @clerk/nextjs is installed/configured. Local/mock mode is fail-closed in production.
        </div>
      </section>
    </main>
  );
}
