import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Component tests opt into jsdom per file; unmounting after each test keeps them isolated.
afterEach(() => {
  cleanup();
});
