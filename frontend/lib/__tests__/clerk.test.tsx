import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  AuthGate,
  ClerkFrontendProvider,
  isLocalMockAuthAllowed,
  MOCK_DEMO_EMAIL,
  MOCK_DEMO_TENANT_ID,
  MOCK_DEMO_TOKEN,
  MOCK_DEMO_USER_ID,
  MOCK_SESSION_KEY,
  type FrontendAuthState,
  useFrontendAuth,
} from "@/lib/clerk";

// Test component that reads auth context
function AuthInspector() {
  const auth = useFrontendAuth();
  return (
    <div>
      <span data-testid="is-loaded">{String(auth.isLoaded)}</span>
      <span data-testid="is-signed-in">{String(auth.isSignedIn)}</span>
      <span data-testid="user-id">{auth.userId ?? "null"}</span>
      <span data-testid="email">{auth.email ?? "null"}</span>
      <span data-testid="tenant-id">{auth.tenantId ?? "null"}</span>
      <span data-testid="mode">{auth.mode ?? "null"}</span>
      <span data-testid="has-sign-in">{typeof auth.mockSignIn === "function" ? "yes" : "no"}</span>
      <span data-testid="has-sign-out">{typeof auth.mockSignOut === "function" ? "yes" : "no"}</span>
    </div>
  );
}

function SignInButton() {
  const auth = useFrontendAuth();
  return (
    <button onClick={() => auth.mockSignIn?.()}>sign-in</button>
  );
}

function SignOutButton() {
  const auth = useFrontendAuth();
  return (
    <button onClick={() => auth.mockSignOut?.()}>sign-out</button>
  );
}

describe("isLocalMockAuthAllowed", () => {
  it("allows mock when NODE_ENV is development", () => {
    expect(isLocalMockAuthAllowed("development", undefined)).toBe(true);
  });

  it("allows mock when NODE_ENV is test", () => {
    expect(isLocalMockAuthAllowed("test", undefined)).toBe(true);
  });

  it("allows mock when NODE_ENV is not set", () => {
    expect(isLocalMockAuthAllowed(undefined, undefined)).toBe(true);
  });

  it("blocks mock in production without explicit flag", () => {
    expect(isLocalMockAuthAllowed("production", undefined)).toBe(false);
  });

  it("allows mock in production when NEXT_PUBLIC_CLERK_MOCK_MODE=true", () => {
    expect(isLocalMockAuthAllowed("production", "true")).toBe(true);
  });

  it("allows mock in production when NEXT_PUBLIC_CLERK_MOCK_MODE=1", () => {
    expect(isLocalMockAuthAllowed("production", "1")).toBe(true);
  });

  it("blocks mock in production with arbitrary flag value", () => {
    expect(isLocalMockAuthAllowed("production", "yes")).toBe(false);
  });
});

describe("ClerkFrontendProvider value override", () => {
  it("passes through a custom value prop directly", () => {
    const customAuth: FrontendAuthState = {
      isLoaded: true,
      isSignedIn: true,
      userId: "custom-user",
      email: "custom@example.com",
      tenantId: "custom-tenant",
      getToken: async () => "custom-token",
      mode: "local_mock",
    };
    render(
      <ClerkFrontendProvider value={customAuth}>
        <AuthInspector />
      </ClerkFrontendProvider>,
    );
    expect(screen.getByTestId("is-signed-in").textContent).toBe("true");
    expect(screen.getByTestId("user-id").textContent).toBe("custom-user");
    expect(screen.getByTestId("email").textContent).toBe("custom@example.com");
    expect(screen.getByTestId("tenant-id").textContent).toBe("custom-tenant");
  });
});

describe("MockAuthProvider (no value override)", () => {
  let localStorageMock: Record<string, string>;

  beforeEach(() => {
    localStorageMock = {};
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => localStorageMock[key] ?? null,
      setItem: (key: string, value: string) => { localStorageMock[key] = value; },
      removeItem: (key: string) => { delete localStorageMock[key]; },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts with isLoaded=false and isSignedIn=false before useEffect", () => {
    render(
      <ClerkFrontendProvider>
        <AuthInspector />
      </ClerkFrontendProvider>,
    );
    // Before useEffect fires, isLoaded is false (SSR-safe default)
    // After useEffect, isLoaded becomes true
    // In test environment, effects run synchronously after act()
    // So we check the final stable state after hydration
    expect(screen.getByTestId("is-signed-in").textContent).toBe("false");
  });

  it("exposes mockSignIn and mockSignOut in non-production", async () => {
    render(
      <ClerkFrontendProvider>
        <AuthInspector />
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("is-loaded").textContent).toBe("true"));
    expect(screen.getByTestId("has-sign-in").textContent).toBe("yes");
    expect(screen.getByTestId("has-sign-out").textContent).toBe("yes");
  });

  it("mockSignIn sets isSignedIn=true with correct demo identity", async () => {
    render(
      <ClerkFrontendProvider>
        <AuthInspector />
        <SignInButton />
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("is-loaded").textContent).toBe("true"));
    expect(screen.getByTestId("is-signed-in").textContent).toBe("false");

    act(() => { screen.getByRole("button", { name: "sign-in" }).click(); });

    await waitFor(() => expect(screen.getByTestId("is-signed-in").textContent).toBe("true"));
    expect(screen.getByTestId("user-id").textContent).toBe(MOCK_DEMO_USER_ID);
    expect(screen.getByTestId("email").textContent).toBe(MOCK_DEMO_EMAIL);
    expect(screen.getByTestId("tenant-id").textContent).toBe(MOCK_DEMO_TENANT_ID);
    expect(screen.getByTestId("mode").textContent).toBe("local_mock");
  });

  it("mockSignIn token resolves to MOCK_DEMO_TOKEN", async () => {
    let capturedToken: string | null = null;
    function TokenInspector() {
      const auth = useFrontendAuth();
      return (
        <button onClick={async () => { capturedToken = await auth.getToken(); }}>get-token</button>
      );
    }
    render(
      <ClerkFrontendProvider>
        <SignInButton />
        <TokenInspector />
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "sign-in" })).toBeTruthy());
    act(() => { screen.getByRole("button", { name: "sign-in" }).click(); });
    await act(async () => { screen.getByRole("button", { name: "get-token" }).click(); });
    expect(capturedToken).toBe(MOCK_DEMO_TOKEN);
  });

  it("mockSignOut returns to signed-out state", async () => {
    render(
      <ClerkFrontendProvider>
        <AuthInspector />
        <SignInButton />
        <SignOutButton />
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("is-loaded").textContent).toBe("true"));

    act(() => { screen.getByRole("button", { name: "sign-in" }).click(); });
    await waitFor(() => expect(screen.getByTestId("is-signed-in").textContent).toBe("true"));

    act(() => { screen.getByRole("button", { name: "sign-out" }).click(); });
    await waitFor(() => expect(screen.getByTestId("is-signed-in").textContent).toBe("false"));
    expect(screen.getByTestId("user-id").textContent).toBe("null");
    expect(screen.getByTestId("tenant-id").textContent).toBe("null");
  });

  it("mockSignIn persists session to localStorage", async () => {
    render(
      <ClerkFrontendProvider>
        <SignInButton />
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "sign-in" })).toBeTruthy());
    act(() => { screen.getByRole("button", { name: "sign-in" }).click(); });
    await waitFor(() => expect(localStorageMock[MOCK_SESSION_KEY]).toBe("1"));
  });

  it("mockSignOut removes session from localStorage", async () => {
    localStorageMock[MOCK_SESSION_KEY] = "1";
    render(
      <ClerkFrontendProvider>
        <SignOutButton />
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "sign-out" })).toBeTruthy());
    act(() => { screen.getByRole("button", { name: "sign-out" }).click(); });
    await waitFor(() => expect(localStorageMock[MOCK_SESSION_KEY]).toBeUndefined());
  });

  it("hydrates from localStorage — mounts as signed in if session key present", async () => {
    localStorageMock[MOCK_SESSION_KEY] = "1";
    render(
      <ClerkFrontendProvider>
        <AuthInspector />
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("is-signed-in").textContent).toBe("true"));
    expect(screen.getByTestId("user-id").textContent).toBe(MOCK_DEMO_USER_ID);
    expect(screen.getByTestId("tenant-id").textContent).toBe(MOCK_DEMO_TENANT_ID);
  });
});

describe("AuthGate production block", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows production block when mode=local_mock in production without mock flag", () => {
    const productionBlockedAuth: FrontendAuthState = {
      isLoaded: true,
      isSignedIn: false,
      userId: null,
      email: null,
      tenantId: null,
      mode: "local_mock",
      getToken: async () => null,
    };
    // Simulate production env
    vi.stubEnv("NODE_ENV", "production");

    render(
      <ClerkFrontendProvider value={productionBlockedAuth}>
        <AuthGate>
          <div>protected content</div>
        </AuthGate>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByText(/Production auth blocked/i)).toBeTruthy();
    expect(screen.queryByText("protected content")).toBeNull();
  });
});
