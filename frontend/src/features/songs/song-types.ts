export type Difficulty = "tutorial" | "easy" | "normal" | "hard" | "expert";
export type SongStatus = "draft" | "published" | "archived";

export interface Song {
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
  items: Song[];
  total: number;
  page: number;
  page_size: number;
}

export interface SongQuery {
  page: number;
  page_size: number;
  q?: string;
  status?: SongStatus;
  difficulty?: Difficulty;
}

export interface ChartSummary {
  id: string;
  revision_number: number;
  schema_version: number;
  beatmap_id: number;
  note_count: number;
  unsupported_count: number;
  first_beat: number | null;
  last_beat: number | null;
}
