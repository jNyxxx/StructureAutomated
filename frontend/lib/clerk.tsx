"use client";

import { createContext, type ReactNode, useContext, useMemo, useState, useEffect } from "react";

import { AuthCard, type AuthCardMode } from "@/components/public/auth-card";
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

const isMockSignedIn = typeof window !== "undefined" && localStorage.getItem("mock_signed_in") === "true";

const localMockState: FrontendAuthState = {
  isLoaded: true,
  isSignedIn: isMockSignedIn,
  userId: isMockSignedIn ? "user_clerk_1" : null,
  email: isMockSignedIn ? "owner@example.com" : null,
  mode: "local_mock",
  getToken: async () => isMockSignedIn ? "mock_token" : null,
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
  const [isMounted, setIsMounted] = useState(false);
  const [isSignedIn, setIsSignedIn] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const signedIn = typeof window !== "undefined" && localStorage.getItem("mock_signed_in") === "true";
    setIsSignedIn(signedIn);
  }, []);

  const state = useMemo<FrontendAuthState>(() => {
    if (value) return value;

    if (!isLocalMockAuthAllowed()) {
      return blockedMockState();
    }

    if (!isMounted) {
      // Return a non-loaded state during SSR/hydration to match server HTML.
      return {
        isLoaded: false,
        isSignedIn: false,
        userId: null,
        email: null,
        mode: "local_mock",
        getToken: async () => null,
      };
    }

    return {
      isLoaded: true,
      isSignedIn: isSignedIn,
      userId: isSignedIn ? "user_clerk_1" : null,
      email: isSignedIn ? "owner@example.com" : null,
      mode: "local_mock",
      getToken: async () => isSignedIn ? "mock_token" : null,
    };
  }, [value, isMounted, isSignedIn]);

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
          
        </div>
      </AuthShell>
    );
  }

  return <>{children}</>;
}

export function ClerkAuthCard({ mode }: { mode: AuthCardMode }) {
  if (!isLocalMockAuthAllowed()) {
    return <MockAuthProductionBlock />;
  }

  return <AuthCard mode={mode} />;
}
