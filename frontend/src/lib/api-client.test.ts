import { describe, expect, it, vi } from "vitest";
import {
  ApiError,
  ConflictError,
  MissingCsrfTokenError,
  NetworkError,
  RateLimitedError,
  UnauthorizedError,
  createApiClient,
} from "./api-client";

const CSRF_COOKIE = "beatstar_admin_csrf";
const CSRF_TOKEN = "token-abc-123";

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

function fakeFetch(response: Response | Error) {
  return vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
    if (response instanceof Error) throw response;
    return response.clone();
  });
}

function cookies(values: Record<string, string>) {
  return (name: string) => values[name];
}

function clientWith(fetchImpl: ReturnType<typeof fakeFetch>, extra: Partial<Parameters<typeof createApiClient>[0]> = {}) {
  return createApiClient({
    baseUrl: "/api/admin",
    fetch: fetchImpl as unknown as typeof fetch,
    readCookie: cookies({ [CSRF_COOKIE]: CSRF_TOKEN }),
    ...extra,
  });
}

function sentHeaders(fetchImpl: ReturnType<typeof fakeFetch>, call = 0): Headers {
  const init = fetchImpl.mock.calls[call]?.[1];
  return new Headers(init?.headers);
}

describe("write requests carry the CSRF token from the browser cookie", () => {
  it("sends the cookie value as X-CSRF-Token on POST", async () => {
    const fetchImpl = fakeFetch(jsonResponse(201, { id: "song-1" }));

    await clientWith(fetchImpl).post("/songs", { title: "T", artist: "A", difficulty: "normal" });

    expect(sentHeaders(fetchImpl).get("X-CSRF-Token")).toBe(CSRF_TOKEN);
  });

  it("sends the token on PATCH and DELETE as well", async () => {
    const fetchImpl = fakeFetch(jsonResponse(200, {}));
    const client = clientWith(fetchImpl);

    await client.patch("/songs/song-1", { expected_revision: 1, title: "New" });
    await client.delete("/songs/song-1", { expected_revision: 2 });

    expect(sentHeaders(fetchImpl, 0).get("X-CSRF-Token")).toBe(CSRF_TOKEN);
    expect(sentHeaders(fetchImpl, 1).get("X-CSRF-Token")).toBe(CSRF_TOKEN);
  });

  it("refuses to send a write when the CSRF cookie is absent", async () => {
    const fetchImpl = fakeFetch(jsonResponse(201, {}));
    const client = clientWith(fetchImpl, { readCookie: cookies({}) });

    await expect(client.post("/songs", {})).rejects.toBeInstanceOf(MissingCsrfTokenError);
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});

describe("read requests", () => {
  it("never send the CSRF header", async () => {
    const fetchImpl = fakeFetch(jsonResponse(200, { items: [] }));

    await clientWith(fetchImpl).get("/songs", { q: "sweet" });

    expect(sentHeaders(fetchImpl).has("X-CSRF-Token")).toBe(false);
  });

  it("encode query parameters and skip empty ones", async () => {
    const fetchImpl = fakeFetch(jsonResponse(200, { items: [] }));

    await clientWith(fetchImpl).get("/songs", { q: "sweet home", status: undefined, page: 2 });

    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/api/admin/songs?q=sweet+home&page=2");
  });
});

describe("every request", () => {
  it("is sent with same-origin credentials so the session cookie travels", async () => {
    const fetchImpl = fakeFetch(jsonResponse(200, {}));

    await clientWith(fetchImpl).get("/me");

    expect(fetchImpl.mock.calls[0]?.[1]?.credentials).toBe("same-origin");
  });
});

describe("error mapping", () => {
  it("maps 409 to ConflictError carrying the current revision", async () => {
    const fetchImpl = fakeFetch(jsonResponse(409, { detail: "Song changed", current_revision: 4 }));

    const failure = await clientWith(fetchImpl).patch("/songs/s", { expected_revision: 3, title: "x" }).catch((e) => e);

    expect(failure).toBeInstanceOf(ConflictError);
    expect((failure as ConflictError).currentRevision).toBe(4);
    expect((failure as ConflictError).message).toBe("Song changed");
  });

  it("maps 401 to UnauthorizedError and notifies the session handler once", async () => {
    const onUnauthorized = vi.fn();
    const fetchImpl = fakeFetch(jsonResponse(401, { detail: "Unauthorized" }));

    const failure = await clientWith(fetchImpl, { onUnauthorized }).get("/me").catch((e) => e);

    expect(failure).toBeInstanceOf(UnauthorizedError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it.each([
    [415, "Formato de arquivo não suportado"],
    [413, "Arquivo excede o limite por tipo"],
    [422, "Audio has no readable duration"],
    [403, "Token CSRF inválido"],
  ])("maps %i to ApiError keeping the server's detail", async (status, detail) => {
    const fetchImpl = fakeFetch(jsonResponse(status, { detail }));

    const failure = await clientWith(fetchImpl).get("/songs").catch((e) => e);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).status).toBe(status);
    expect((failure as ApiError).message).toBe(detail);
  });

  it("maps 429 to RateLimitedError with the Retry-After delay", async () => {
    const fetchImpl = fakeFetch(
      jsonResponse(429, { detail: "Muitas tentativas" }, { "retry-after": "42" }),
    );

    const failure = await clientWith(fetchImpl).post("/auth/login", {}).catch((e) => e);

    expect(failure).toBeInstanceOf(RateLimitedError);
    expect((failure as RateLimitedError).retryAfterSeconds).toBe(42);
  });

  it("reports a non-JSON error body as an ApiError without crashing", async () => {
    const fetchImpl = fakeFetch(new Response("<html>bad gateway</html>", { status: 502 }));

    const failure = await clientWith(fetchImpl).get("/songs").catch((e) => e);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).status).toBe(502);
  });

  it("surfaces a network failure as NetworkError instead of swallowing it", async () => {
    const fetchImpl = fakeFetch(new TypeError("Failed to fetch"));

    const failure = await clientWith(fetchImpl).get("/songs").catch((e) => e);

    expect(failure).toBeInstanceOf(NetworkError);
  });
});

describe("login is the only write that works before a session exists", () => {
  it("posts credentials as form-encoded fields without requiring a CSRF cookie", async () => {
    const fetchImpl = fakeFetch(new Response(null, { status: 204 }));
    const client = clientWith(fetchImpl, { readCookie: cookies({}) });

    await client.postForm("/auth/login", { username: "admin@example.com", password: "s3cret" });

    const init = fetchImpl.mock.calls[0]?.[1];
    expect(sentHeaders(fetchImpl).get("Content-Type")).toBe("application/x-www-form-urlencoded");
    expect(String(init?.body)).toBe("username=admin%40example.com&password=s3cret");
    expect(sentHeaders(fetchImpl).has("X-CSRF-Token")).toBe(false);
  });

  it("maps a rejected login to UnauthorizedError and does not trigger the session-expired handler", async () => {
    const onUnauthorized = vi.fn();
    const fetchImpl = fakeFetch(jsonResponse(401, { detail: "Credenciais inválidas" }));
    const client = clientWith(fetchImpl, { readCookie: cookies({}), onUnauthorized });

    const failure = await client
      .postForm("/auth/login", { username: "a@example.com", password: "wrong" })
      .catch((e) => e);

    expect(failure).toBeInstanceOf(UnauthorizedError);
    expect((failure as Error).message).toBe("Credenciais inválidas");
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
