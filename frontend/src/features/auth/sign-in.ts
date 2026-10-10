import type { ApiClient } from "../../lib/api-client";
import type { Credentials } from "./login-form";

/** Builds the sign-in action: the server's OAuth2 password form names the e-mail field "username". */
export function createSignIn(client: ApiClient): (credentials: Credentials) => Promise<void> {
  return async (credentials) => {
    await client.postForm("/auth/login", { username: credentials.email, password: credentials.password });
  };
}
