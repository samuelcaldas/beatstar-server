import { createApiClient } from "../../lib/api-client";
import { readCookie } from "../../lib/cookies";

/** Creates the same-origin administration client with the existing CSRF cookie convention. */
export function createSongAdminClient() {
  return createApiClient({
    baseUrl: "/api/admin",
    fetch: (input, init) => fetch(input, init),
    readCookie: (name) => readCookie(document.cookie, name),
  });
}
