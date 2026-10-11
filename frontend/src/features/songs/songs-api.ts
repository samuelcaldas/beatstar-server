/**
 * Typed calls to the song library and its charts and artwork. Every method goes through the
 * shared admin client, so writes carry the CSRF token and failures keep their typed errors.
 */

import type { ApiClient } from "../../lib/api-client";
import type { ChartNote, Difficulty } from "./song-format";

export const SONGS_PATH = "/songs";
export const ADMIN_API_BASE = "/api/admin";

export type SongStatus = "draft" | "published" | "archived";

export interface SongRecord {
  id: string;
  title: string;
  artist: string;
  difficulty: Difficulty;
  game_song_id: number | null;
  beatmap_id: number | null;
  bpm: number | null;
  time_signature: number | null;
  variant_label: string | null;
  source: "manual" | "unity-import" | "example";
  status: SongStatus;
  revision: number;
  created_at: number;
  updated_at: number;
}

export interface SongPage {
  items: SongRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChartRecord {
  id: string;
  song_id: string;
  revision_number: number;
  schema_version: number;
  beatmap_id: number;
  id_label: string;
  note_count: number;
  unsupported_count: number;
  lanes: Record<string, number>;
  first_beat: number | null;
  last_beat: number | null;
  raw_sha256: string;
  created_at: number;
}

export interface AssetRecord {
  id: string;
  song_id: string;
  kind: "audio" | "artwork";
  sha256: string;
  byte_size: number;
  content_type: string;
  width: number | null;
  height: number | null;
  created_at: number;
}

export interface SongDraftInput {
  title: string;
  artist: string;
  difficulty: Difficulty;
  game_song_id?: number | null;
  beatmap_id?: number | null;
  bpm?: number | null;
  time_signature?: number | null;
  variant_label?: string | null;
}

export interface SongGameFieldsInput {
  bpm?: number;
  time_signature?: number;
  variant_label?: string;
  expected_revision: number;
}

export interface SongListQuery {
  page: number;
  page_size: number;
  q?: string;
  status?: SongStatus;
}

export interface SongLibrary {
  list(query: SongListQuery): Promise<SongPage>;
  create(input: SongDraftInput): Promise<SongRecord>;
  updateGameFields(songId: string, input: SongGameFieldsInput): Promise<SongRecord>;
  archive(songId: string, revision: number): Promise<SongRecord>;
  restore(songId: string, revision: number): Promise<SongRecord>;
  charts(songId: string): Promise<ChartRecord[]>;
  createChart(songId: string, notes: ChartNote[]): Promise<ChartRecord>;
  assets(songId: string): Promise<AssetRecord[]>;
  uploadArtwork(songId: string, file: Blob, contentType: string): Promise<AssetRecord>;
}

export function createSongLibrary(client: ApiClient): SongLibrary {
  return {
    list: (query) => client.get<SongPage>(SONGS_PATH, { ...query }),
    create: (input) => client.post<SongRecord>(SONGS_PATH, input),
    updateGameFields: (songId, input) => client.patch<SongRecord>(`${SONGS_PATH}/${songId}`, input),
    archive: (songId, revision) =>
      client.post<SongRecord>(`${SONGS_PATH}/${songId}/archive`, { expected_revision: revision }),
    restore: (songId, revision) =>
      client.post<SongRecord>(`${SONGS_PATH}/${songId}/restore`, { expected_revision: revision }),
    charts: (songId) => client.get<ChartRecord[]>(`${SONGS_PATH}/${songId}/charts`),
    createChart: (songId, notes) => client.post<ChartRecord>(`${SONGS_PATH}/${songId}/charts`, { notes }),
    assets: (songId) => client.get<AssetRecord[]>(`${SONGS_PATH}/${songId}/assets`),
    uploadArtwork: (songId, file, contentType) =>
      client.putRaw<AssetRecord>(`${SONGS_PATH}/${songId}/assets/artwork`, file, contentType),
  };
}

/** Returns the same-origin URL that previews a stored asset; the session cookie authorises it. */
export function assetContentUrl(assetId: string): string {
  return `${ADMIN_API_BASE}/assets/${assetId}/content`;
}
