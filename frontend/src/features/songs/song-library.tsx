"use client";

import { useCallback, useEffect, useState } from "react";
import { describeFailure } from "./describe-failure";
import { SongCreateForm } from "./song-create-form";
import { SongDetail } from "./song-detail";
import { difficultyLabel, formatTempo } from "./song-format";
import type { SongLibrary, SongRecord, SongStatus } from "./songs-api";

const PAGE_SIZE = 20;

interface SongLibraryProps {
  library: SongLibrary;
}

/** Lists songs with search and status filters, creates drafts, and opens one song for review. */
export function SongLibraryView({ library }: SongLibraryProps) {
  const [songs, setSongs] = useState<SongRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<SongStatus | "">("");
  const [selected, setSelected] = useState<SongRecord | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadSongs = useCallback(async () => {
    try {
      const result = await library.list({
        page,
        page_size: PAGE_SIZE,
        q: search.trim() || undefined,
        status: status || undefined,
      });
      setSongs(result.items);
      setTotal(result.total);
      setMessage(null);
    } catch (failure) {
      setMessage(describeFailure(failure));
    }
  }, [library, page, search, status]);

  useEffect(() => {
    void loadSongs();
  }, [loadSongs]);

  function handleCreated(song: SongRecord) {
    setSelected(song);
    setPage(1);
    void loadSongs();
  }

  function handleChanged(song: SongRecord) {
    setSelected(song);
    setSongs((current) => current.map((item) => (item.id === song.id ? song : item)));
  }

  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section aria-label="Biblioteca de músicas">
      <h2>Biblioteca de músicas</h2>
      <div>
        <label>Buscar <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>
        <label>
          Situação
          <select value={status} onChange={(event) => { setStatus(event.target.value as SongStatus | ""); setPage(1); }}>
            <option value="">Todas</option>
            <option value="draft">Rascunho</option>
            <option value="published">Publicada</option>
            <option value="archived">Arquivada</option>
          </select>
        </label>
      </div>
      {message !== null && <p role="alert">{message}</p>}
      <table>
        <thead>
          <tr>
            <th>Título</th><th>Artista</th><th>Dificuldade</th><th>Andamento</th>
            <th>ID jogo</th><th>Beatmap</th><th>Origem</th><th>Situação</th>
          </tr>
        </thead>
        <tbody>
          {songs.map((song) => (
            <tr key={song.id} aria-selected={selected?.id === song.id} onClick={() => setSelected(song)}>
              <td>{song.title}</td>
              <td>{song.artist}</td>
              <td>{difficultyLabel(song.difficulty)}</td>
              <td>{formatTempo(song.bpm, song.time_signature)}</td>
              <td>{song.game_song_id ?? "—"}</td>
              <td>{song.beatmap_id ?? "—"}</td>
              <td>{song.source}</td>
              <td>{song.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <nav aria-label="Paginação">
        <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
        <span> Página {page} de {lastPage} ({total} músicas) </span>
        <button type="button" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>Próxima</button>
      </nav>
      <SongCreateForm library={library} onCreated={handleCreated} />
      {selected !== null && <SongDetail key={selected.id} library={library} song={selected} onChanged={handleChanged} />}
    </section>
  );
}
