import { describe, expect, it } from "vitest";
import { readCookie } from "./cookies";

describe("readCookie", () => {
  it("returns the value of the named cookie from a document.cookie string", () => {
    expect(readCookie("theme=dark; beatstar_admin_csrf=abc123", "beatstar_admin_csrf")).toBe("abc123");
  });

  it("returns undefined when the cookie is absent", () => {
    expect(readCookie("theme=dark", "beatstar_admin_csrf")).toBeUndefined();
  });

  it("does not match a cookie whose name merely ends with the requested name", () => {
    expect(readCookie("old_beatstar_admin_csrf=stale", "beatstar_admin_csrf")).toBeUndefined();
  });

  it("returns an empty cookie value as undefined so a missing token is detected", () => {
    expect(readCookie("beatstar_admin_csrf=", "beatstar_admin_csrf")).toBeUndefined();
  });
});
