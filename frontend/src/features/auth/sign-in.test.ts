import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "../../lib/api-client";
import { createSignIn } from "./sign-in";

function clientRecording() {
  const fetchImpl = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(null, { status: 204 }));
  const client = createApiClient({
    baseUrl: "/api/admin",
    fetch: fetchImpl as unknown as typeof fetch,
    readCookie: () => undefined,
  });
  return { client, fetchImpl };
}

describe("createSignIn", () => {
  it("posts the e-mail as the OAuth2 username field the server expects", async () => {
    const { client, fetchImpl } = clientRecording();

    await createSignIn(client)({ email: "admin@example.com", password: "s3cret" });

    const [url, init] = fetchImpl.mock.calls[0] ?? [];
    expect(url).toBe("/api/admin/auth/login");
    expect(init?.method).toBe("POST");
    expect(String(init?.body)).toBe("username=admin%40example.com&password=s3cret");
  });
});
