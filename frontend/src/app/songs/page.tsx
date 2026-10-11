"use client";

import { useMemo } from "react";
import { SongList } from "../../features/songs/song-list";
import { createSongAdminClient } from "../../features/songs/admin-client";
import { listSongs } from "../../features/songs/song-api";

/** Authenticated song library route. */
export default function SongsPage() {
  const client = useMemo(() => createSongAdminClient(), []);
  const loadSongs = useMemo(() => (query: Parameters<typeof listSongs>[1]) => listSongs(client, query), [client]);
  return <SongList loadSongs={loadSongs} />;
}
