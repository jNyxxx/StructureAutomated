import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BillingPage from "../(app)/billing/page";
import DashboardPage from "../(app)/dashboard/page";
import LoginPage from "../(auth)/login/page";

describe("route shells render", () => {
  it("renders the login shell heading", () => {
    render(<LoginPage />);
    // getByRole throws if the heading is absent, so this asserts presence.
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeTruthy();
  });

  it("renders the dashboard shell heading", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeTruthy();
  });

  it("renders the billing shell heading", () => {
    render(<BillingPage />);
    expect(screen.getByRole("heading", { name: /billing/i })).toBeTruthy();
  });
});
