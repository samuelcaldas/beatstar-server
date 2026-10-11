"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Difficulty, Song, SongPage, SongStatus } from "./song-types";

const PAGE_SIZE = 20;
const DIFFICULTIES: Difficulty[] = ["tutorial", "easy", "normal", "hard", "expert"];

export interface SongListProps {
  loadSongs: (query: { page: number; page_size: number; q?: string; status?: SongStatus; difficulty?: Difficulty }) => Promise<SongPage>;
}

/** Lists songs with backend-backed search, status, difficulty, and pagination filters. */
export function SongList({ loadSongs }: SongListProps) {
  const [items, setItems] = useState<Song[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<SongStatus | "">("");
  const [difficulty, setDifficulty] = useState<Difficulty | "">("");
  const [error, setError] = useState("");
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    let active = true;
    const query = { page, page_size: PAGE_SIZE, q: search || undefined, status: status || undefined, difficulty: difficulty || undefined };
    loadSongs(query).then((result) => {
      if (!active) return;
      setItems(result.items);
      setTotal(result.total);
      setError("");
    }).catch(() => active && setError("Não foi possível carregar a biblioteca."));
    return () => { active = false; };
  }, [loadSongs, page, search, status, difficulty]);

  return (
    <main style={{ maxWidth: 1120, margin: "0 auto", padding: 32, color: "#e9edf3", background: "#10151d", minHeight: "100vh", fontFamily: "system-ui" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div><p style={{ color: "#a6b1c2", letterSpacing: 2 }}>ADMINISTRAÇÃO / CATÁLOGO</p><h1>Biblioteca de músicas</h1><p>Valide metadados e estado do conteúdo importado.</p></div>
        <span>{total} faixas</span>
      </header>
      <section aria-label="Filtros da biblioteca" style={{ display: "flex", gap: 12, margin: "24px 0" }}>
        <label>Buscar <input aria-label="Buscar música" value={search} onChange={(event) => { setPage(1); setSearch(event.target.value); }} placeholder="Título ou artista" /></label>
        <label>Filtrar por status <select value={status} onChange={(event) => { setPage(1); setStatus(event.target.value as SongStatus | ""); }}><option value="">Todos os status</option><option value="draft">Rascunho</option><option value="published">Publicado</option><option value="archived">Arquivado</option></select></label>
        <label>Filtrar por dificuldade <select value={difficulty} onChange={(event) => { setPage(1); setDifficulty(event.target.value as Difficulty | ""); }}><option value="">Todas as dificuldades</option>{DIFFICULTIES.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
      </section>
      {error && <p role="alert">{error}</p>}
      <div style={{ overflowX: "auto" }}><table style={{ width: "100%", borderCollapse: "collapse" }}><thead><tr><th scope="col">Música</th><th scope="col">Dificuldade</th><th scope="col">Status</th><th scope="col">Revisão</th><th scope="col">Ação</th></tr></thead><tbody>{items.map((song) => <tr key={song.id}><th scope="row">{song.title}<small style={{ display: "block", color: "#a6b1c2" }}>{song.artist}</small></th><td>{song.difficulty}</td><td>{song.status}</td><td>r{song.revision}</td><td><Link href={`/songs/${encodeURIComponent(song.id)}/`}>Abrir detalhes</Link></td></tr>)}</tbody></table></div>
      {!error && items.length === 0 && <p>Nenhuma música encontrada para esses filtros.</p>}
      <nav aria-label="Paginação" style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 24 }}><button aria-label="Página anterior" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button><span>Página {page} de {pageCount}</span><button aria-label="Próxima página" disabled={page >= pageCount} onClick={() => setPage(page + 1)}>Próxima página</button></nav>
    </main>
  );
}
