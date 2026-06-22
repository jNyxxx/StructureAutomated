"use client";

import { createContext, type ReactNode, useContext, useMemo } from "react";

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

function MockAuthProductionBlock() {
  return (
    <main className="min-h-screen p-8">
      <section className="max-w-xl rounded-lg border border-red-200 bg-red-50 p-6">
        <h1 className="text-xl font-semibold text-red-950">Production auth blocked</h1>
        <p className="mt-2 text-sm text-red-900">
          Local/mock Clerk auth cannot run silently in production. Configure the real Clerk provider
          before enabling protected app routes.
        </p>
      </section>
    </main>
  );
}

export function AuthGate({ children }: { children: ReactNode }) {
  const auth = useFrontendAuth();

  if (auth.mode === "local_mock" && !isLocalMockAuthAllowed()) {
    return <MockAuthProductionBlock />;
  }

  if (!auth.isLoaded) {
    return (
      <main className="min-h-screen p-8">
        <div className="rounded-lg border p-6 text-sm text-slate-600">Loading secure session…</div>
      </main>
    );
  }

  if (!auth.isSignedIn) {
    return (
      <main className="min-h-screen p-8">
        <section className="max-w-xl rounded-lg border border-amber-200 bg-amber-50 p-6">
          <h1 className="text-xl font-semibold text-amber-950">Authentication required</h1>
          <p className="mt-2 text-sm text-amber-900">
            App routes are protected. Sign in through Clerk before accessing tenant data.
          </p>
          <a className="mt-4 inline-block text-sm font-medium underline" href="/login">
            Go to sign in
          </a>
        </section>
      </main>
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
    <main className="min-h-screen p-8">
      <section className="max-w-lg rounded-xl border bg-white p-6 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Clerk auth — local/mock mount
        </p>
        <h1 className="mt-2 text-xl font-semibold">{copy.title}</h1>
        <p className="mt-2 text-sm text-slate-600">{copy.body}</p>
        <div className="mt-5 rounded-lg border border-dashed p-4 text-sm text-slate-600">
          {copy.action} plugs in here when @clerk/nextjs is installed/configured. Local/mock mode is
          fail-closed in production.
        </div>
      </section>
    </main>
  );
}
