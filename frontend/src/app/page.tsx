"use client";

import { useState } from "react";
import { LoginForm } from "../features/auth/login-form";
import { createSignIn } from "../features/auth/sign-in";
import { createApiClient } from "../lib/api-client";
import { readCookie } from "../lib/cookies";

const client = createApiClient({
  baseUrl: "/api/admin",
  fetch: (input, init) => fetch(input, init),
  readCookie: (name) => readCookie(document.cookie, name),
});

/** Administration entry point: shows the sign-in form until the server accepts the session. */
export default function AdministrationEntry() {
  const [signedIn, setSignedIn] = useState(false);

  if (signedIn) {
    return <main><p>Sessão iniciada.</p></main>;
  }
  return (
    <main>
      <h1>Administração Beatstar</h1>
      <LoginForm signIn={createSignIn(client)} onSignedIn={() => setSignedIn(true)} />
    </main>
  );
}
