import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Unmount React trees between tests to keep the jsdom container isolated.
afterEach(() => {
  cleanup();
});
