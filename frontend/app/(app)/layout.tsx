import type { ReactNode } from "react";

// Minimal authenticated-area shell. Tenant context, navigation, and the billing
// banner are wired in Slice 18; this slice only establishes the route group.
export default function AppLayout({ children }: { children: ReactNode }) {
  return <div className="min-h-screen p-8">{children}</div>;
}
