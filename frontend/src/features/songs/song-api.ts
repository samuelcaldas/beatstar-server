import type { ApiClient } from "../../lib/api-client";
import { withExpectedRevision } from "./chart-model";
import type { ChartSummary, Song, SongPage, SongQuery } from "./song-types";

/** Reads a page of songs using the backend's SongQuery parameter names. */
export function listSongs(client: ApiClient, query: SongQuery): Promise<SongPage> {
  return client.get<SongPage>("/songs", { page: query.page, page_size: query.page_size, q: query.q, status: query.status, difficulty: query.difficulty });
}

/** Reads a song and its immutable chart summaries. */
export async function readSong(client: ApiClient, songId: string): Promise<{ song: Song; charts: ChartSummary[] }> {
  const song = await client.get<Song>(`/songs/${encodeURIComponent(songId)}`);
  const charts = await client.get<ChartSummary[]>(`/songs/${encodeURIComponent(songId)}/charts`);
  return { song, charts };
}

/** Sends editable metadata with the revision observed by the caller. */
export function updateSong(client: ApiClient, song: Song, changes: Record<string, unknown>): Promise<Song> {
  return client.patch<Song>(`/songs/${encodeURIComponent(song.id)}`, withExpectedRevision(changes, song.revision));
}

/** Applies a confirmed archive, restore, or delete transition. */
export function changeSongState(client: ApiClient, song: Song, action: "archive" | "restore" | "delete"): Promise<Song | void> {
  const guard = { expected_revision: song.revision };
  if (action === "delete") return client.delete<void>(`/songs/${encodeURIComponent(song.id)}`, guard);
  return client.post<Song>(`/songs/${encodeURIComponent(song.id)}/${action}`, guard);
}
