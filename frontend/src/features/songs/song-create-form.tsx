"use client";

import { useState, type FormEvent } from "react";
import { DIFFICULTIES, DIFFICULTY_LABELS, parseOptionalNumber, type Difficulty } from "./song-format";
import type { SongDraftInput, SongLibrary, SongRecord } from "./songs-api";
import { describeFailure } from "./describe-failure";

interface SongCreateFormProps {
  library: SongLibrary;
  onCreated: (song: SongRecord) => void;
}

/** Creates a draft song with the fields the game uses to identify it. Blank optional fields are omitted. */
export function SongCreateForm({ library, onCreated }: SongCreateFormProps) {
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("normal");
  const [gameSongId, setGameSongId] = useState("");
  const [beatmapId, setBeatmapId] = useState("");
  const [bpm, setBpm] = useState("");
  const [timeSignature, setTimeSignature] = useState("4");
  const [variantLabel, setVariantLabel] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = buildInput({ title, artist, difficulty, gameSongId, beatmapId, bpm, timeSignature, variantLabel });
    if (typeof input === "string") {
      setMessage(input);
      return;
    }
    setPending(true);
    setMessage(null);
    try {
      onCreated(await library.create(input));
      setTitle("");
      setArtist("");
      setGameSongId("");
      setBeatmapId("");
      setBpm("");
      setVariantLabel("");
    } catch (failure) {
      setMessage(describeFailure(failure));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Nova música">
      <h2>Nova música (rascunho)</h2>
      <label>Título <input value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={200} /></label>
      <label>Artista <input value={artist} onChange={(event) => setArtist(event.target.value)} required maxLength={200} /></label>
      <label>
        Dificuldade
        <select value={difficulty} onChange={(event) => setDifficulty(event.target.value as Difficulty)}>
          {DIFFICULTIES.map((value) => (
            <option key={value} value={value}>{DIFFICULTY_LABELS[value]}</option>
          ))}
        </select>
      </label>
      <label>ID da música no jogo <input inputMode="numeric" value={gameSongId} onChange={(event) => setGameSongId(event.target.value)} /></label>
      <label>ID do beatmap <input inputMode="numeric" value={beatmapId} onChange={(event) => setBeatmapId(event.target.value)} /></label>
      <label>BPM <input inputMode="decimal" value={bpm} onChange={(event) => setBpm(event.target.value)} /></label>
      <label>Compasso (batidas por compasso) <input inputMode="numeric" value={timeSignature} onChange={(event) => setTimeSignature(event.target.value)} /></label>
      <label>Rótulo da variante <input value={variantLabel} onChange={(event) => setVariantLabel(event.target.value)} maxLength={64} /></label>
      <button type="submit" disabled={pending}>Criar rascunho</button>
      {message !== null && <p role="alert">{message}</p>}
    </form>
  );
}

interface DraftFields {
  title: string;
  artist: string;
  difficulty: Difficulty;
  gameSongId: string;
  beatmapId: string;
  bpm: string;
  timeSignature: string;
  variantLabel: string;
}

/** Validates the form and returns the request body, or the first problem as a message. */
function buildInput(fields: DraftFields): SongDraftInput | string {
  const gameSongId = parseOptionalNumber(fields.gameSongId);
  const beatmapId = parseOptionalNumber(fields.beatmapId);
  const bpm = parseOptionalNumber(fields.bpm);
  const timeSignature = parseOptionalNumber(fields.timeSignature);
  if ([gameSongId, beatmapId, bpm, timeSignature].includes("invalid")) return "Use apenas números nos campos numéricos";
  const variant = fields.variantLabel.trim();
  if (variant !== "" && !/^[A-Za-z0-9_-]{1,64}$/.test(variant)) {
    return "O rótulo da variante aceita letras, números, - e _ (até 64 caracteres)";
  }
  return {
    title: fields.title.trim(),
    artist: fields.artist.trim(),
    difficulty: fields.difficulty,
    game_song_id: gameSongId as number | null,
    beatmap_id: beatmapId as number | null,
    bpm: bpm as number | null,
    time_signature: timeSignature as number | null,
    variant_label: variant === "" ? null : variant,
  };
}
