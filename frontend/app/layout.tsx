import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ClerkFrontendProvider } from "@/lib/clerk";

import "./globals.css";

export const metadata: Metadata = {
  title: "AutomatedStructure",
  description: "Secure multi-tenant marketing-automation platform.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ClerkFrontendProvider>{children}</ClerkFrontendProvider>
      </body>
    </html>
  );
}
