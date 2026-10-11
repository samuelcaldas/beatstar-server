"use client";

import { useState } from "react";
import { LoginForm } from "../features/auth/login-form";
import { createSignIn } from "../features/auth/sign-in";
import { createSongLibrary, ADMIN_API_BASE } from "../features/songs/songs-api";
import { SongLibraryView } from "../features/songs/song-library";
import { createApiClient } from "../lib/api-client";
import { readCookie } from "../lib/cookies";

const client = createApiClient({
  baseUrl: ADMIN_API_BASE,
  fetch: (input, init) => fetch(input, init),
  readCookie: (name) => readCookie(document.cookie, name),
});
const library = createSongLibrary(client);

/** Administration entry point: sign-in first, then the song library. */
export default function AdministrationEntry() {
  const [signedIn, setSignedIn] = useState(false);

  if (signedIn) {
    return (
      <main>
        <h1>Administração Beatstar</h1>
        <SongLibraryView library={library} />
      </main>
    );
  }
  return (
    <main>
      <h1>Administração Beatstar</h1>
      <LoginForm signIn={createSignIn(client)} onSignedIn={() => setSignedIn(true)} />
    </main>
  );
}
