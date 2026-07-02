"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthCard, type AuthCardMode } from "@/components/public/auth-card";
import { Button } from "@/components/ui/button";
import { LoadingState, LocalMockNotice, PermissionDeniedState } from "@/components/states";

export interface FrontendAuthState {
  isLoaded: boolean;
  isSignedIn: boolean;
  userId: string | null;
  email: string | null;
  tenantId?: string | null;
  getToken: () => Promise<string | null>;
  mode?: "real_clerk" | "local_mock";
  mockSignIn?: () => void;
  mockSignOut?: () => void;
}

export const MOCK_DEMO_TOKEN = "token-sentinel";
export const MOCK_DEMO_USER_ID = "11111111-1111-1111-1111-111111111111";
export const MOCK_DEMO_TENANT_ID = "22222222-2222-2222-2222-222222222222";
export const MOCK_DEMO_EMAIL = "owner@example.com";
export const MOCK_SESSION_KEY = "as_mock_session";

const mockModeFlag = process.env.NEXT_PUBLIC_CLERK_MOCK_MODE;
const MOCK_SESSION_ID_PATTERN = /^[A-Za-z0-9_-]{8,128}$/;

export function isLocalMockAuthAllowed(
  nodeEnv: string | undefined = process.env.NODE_ENV,
  explicitMockMode: string | undefined = mockModeFlag,
): boolean {
  return nodeEnv !== "production" || explicitMockMode === "true" || explicitMockMode === "1";
}

export function createMockDemoToken(): string {
  const cryptoApi = globalThis.crypto;
  const randomId = cryptoApi?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 14)}`;
  const safeId = randomId.replace(/[^A-Za-z0-9_-]/g, "");
  return `${MOCK_DEMO_TOKEN}:${safeId}`;
}

function isValidMockDemoToken(token: string): boolean {
  if (!token.startsWith(`${MOCK_DEMO_TOKEN}:`)) return false;
  const sessionId = token.slice(MOCK_DEMO_TOKEN.length + 1);
  return MOCK_SESSION_ID_PATTERN.test(sessionId);
}

function blockedMockState(): FrontendAuthState {
  return {
    isLoaded: true,
    isSignedIn: false,
    userId: null,
    email: null,
    tenantId: null,
    mode: "local_mock",
    getToken: async () => null,
  };
}

const ClerkContext = createContext<FrontendAuthState>({
  isLoaded: false,
  isSignedIn: false,
  userId: null,
  email: null,
  tenantId: null,
  mode: "local_mock",
  getToken: async () => null,
});

function MockAuthProvider({ children }: { children: ReactNode }) {
  const [mockToken, setMockToken] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const mockSignIn = useCallback(() => {
    if (!isLocalMockAuthAllowed()) return;
    const nextToken = createMockDemoToken();
    localStorage.setItem(MOCK_SESSION_KEY, nextToken);
    setMockToken(nextToken);
  }, []);

  const mockSignOut = useCallback(() => {
    localStorage.removeItem(MOCK_SESSION_KEY);
    setMockToken(null);
  }, []);

  useEffect(() => {
    if (isLocalMockAuthAllowed()) {
      const storedToken = localStorage.getItem(MOCK_SESSION_KEY);
      if (storedToken) {
        const nextToken = isValidMockDemoToken(storedToken) ? storedToken : createMockDemoToken();
        localStorage.setItem(MOCK_SESSION_KEY, nextToken);
        setMockToken(nextToken);
      }
    }
    setIsLoaded(true);
  }, []);

  const state = useMemo<FrontendAuthState>(() => {
    if (!isLocalMockAuthAllowed()) return blockedMockState();
    if (mockToken) {
      return {
        isLoaded: true,
        isSignedIn: true,
        userId: MOCK_DEMO_USER_ID,
        email: MOCK_DEMO_EMAIL,
        tenantId: MOCK_DEMO_TENANT_ID,
        getToken: async () => mockToken,
        mode: "local_mock",
        mockSignIn,
        mockSignOut,
      };
    }
    return {
      isLoaded,
      isSignedIn: false,
      userId: null,
      email: null,
      tenantId: null,
      getToken: async () => null,
      mode: "local_mock",
      mockSignIn,
      mockSignOut,
    };
  }, [mockToken, isLoaded, mockSignIn, mockSignOut]);

  return <ClerkContext.Provider value={state}>{children}</ClerkContext.Provider>;
}

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
  if (value) {
    return <ClerkContext.Provider value={value}>{children}</ClerkContext.Provider>;
  }
  return <MockAuthProvider>{children}</MockAuthProvider>;
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
  const router = useRouter();

  useEffect(() => {
    if (auth.isLoaded && !auth.isSignedIn && auth.mode === "local_mock" && isLocalMockAuthAllowed()) {
      router.push("/login");
    }
  }, [auth.isLoaded, auth.isSignedIn, auth.mode, router]);

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

export function ClerkAuthCard({ mode }: { mode: AuthCardMode }) {
  if (!isLocalMockAuthAllowed()) {
    return <MockAuthProductionBlock />;
  }

  return <AuthCard mode={mode} />;
}
