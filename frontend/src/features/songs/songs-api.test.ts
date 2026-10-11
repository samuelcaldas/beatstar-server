import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "../../lib/api-client";
import { assetContentUrl, createSongLibrary } from "./songs-api";

const CSRF_TOKEN = "token-abc-123";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function libraryWith(response: Response) {
  const fetchImpl = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => response.clone());
  const client = createApiClient({
    baseUrl: "/api/admin",
    fetch: fetchImpl as unknown as typeof fetch,
    readCookie: (name) => (name === "beatstar_admin_csrf" ? CSRF_TOKEN : undefined),
  });
  return { library: createSongLibrary(client), fetchImpl };
}

function firstCall(fetchImpl: ReturnType<typeof libraryWith>["fetchImpl"]): [string, RequestInit | undefined] {
  const call = fetchImpl.mock.calls[0] as unknown as [string, RequestInit | undefined];
  return call;
}

describe("song library requests", () => {
  it("posts authored notes as JSON to the song's chart collection with CSRF", async () => {
    const { library, fetchImpl } = libraryWith(jsonResponse(201, { id: "chart-1" }));

    await library.createChart("song-9", [{ beat_offset: 8, lane: 1 }]);

    const [url, init] = firstCall(fetchImpl);
    expect(url).toBe("/api/admin/songs/song-9/charts");
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe(CSRF_TOKEN);
    expect(JSON.parse(String(init?.body))).toEqual({ notes: [{ beat_offset: 8, lane: 1 }] });
  });

  it("uploads artwork as the raw file with its own content type", async () => {
    const { library, fetchImpl } = libraryWith(jsonResponse(201, { id: "asset-1" }));
    const file = new Blob([new Uint8Array([137, 80, 78, 71])], { type: "image/png" });

    await library.uploadArtwork("song-9", file, "image/png");

    const [url, init] = firstCall(fetchImpl);
    expect(url).toBe("/api/admin/songs/song-9/assets/artwork");
    expect(init?.method).toBe("PUT");
    expect(init?.body).toBe(file);
    expect(new Headers(init?.headers).get("Content-Type")).toBe("image/png");
  });

  it("previews stored assets through the same-origin content route", () => {
    expect(assetContentUrl("asset-7")).toBe("/api/admin/assets/asset-7/content");
  });
});
