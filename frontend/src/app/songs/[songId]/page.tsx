"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createSongAdminClient } from "../../../features/songs/admin-client";
import { chartValidationErrors } from "../../../features/songs/chart-model";
import { ChartPreview } from "../../../features/songs/chart-preview";
import { changeSongState, readSong, updateSong } from "../../../features/songs/song-api";
import type { ChartSummary, Difficulty, Song } from "../../../features/songs/song-types";

const DIFFICULTIES: Difficulty[] = ["tutorial", "easy", "normal", "hard", "expert"];

/** Loads and manages one song's metadata, state, and available chart summaries. */
export default function SongDetailPage() {
  const params = useParams<{ songId: string }>();
  const router = useRouter();
  const client = useMemo(() => createSongAdminClient(), []);
  const [song, setSong] = useState<Song>();
  const [charts, setCharts] = useState<ChartSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const refresh = useCallback(async () => {
    try {
      const result = await readSong(client, params.songId);
      setSong(result.song);
      setCharts(result.charts);
    } catch {
      setError("Não foi possível carregar a música. Verifique sua sessão e tente novamente.");
    }
  }, [client, params.songId]);
  useEffect(() => { void refresh(); }, [refresh]);

  const saveMetadata = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!song) return;
    const form = new FormData(event.currentTarget);
    const changes = { title: String(form.get("title")).trim(), artist: String(form.get("artist")).trim(), difficulty: String(form.get("difficulty")) as Difficulty };
    setBusy(true);
    try {
      setSong(await updateSong(client, song, changes));
      setNotice("Metadados salvos com a revisão atual.");
      setError("");
    } catch (failure) {
      await handleFailure(failure, refresh, setError);
    } finally { setBusy(false); }
  };

  const transition = async (action: "archive" | "restore" | "delete") => {
    if (!song || !window.confirm(confirmation(action, song.title))) return;
    setBusy(true);
    try {
      await changeSongState(client, song, action);
      if (action === "delete") { router.push("/songs/"); return; }
      await refresh();
      setNotice(action === "archive" ? "Música arquivada." : "Música restaurada como rascunho.");
    } catch (failure) {
      await handleFailure(failure, refresh, setError);
    } finally { setBusy(false); }
  };

  if (!song) return <main style={pageStyle}><Link href="/songs/">← Biblioteca</Link><p role={error ? "alert" : undefined}>{error || "Carregando música…"}</p></main>;
  const chartErrors = charts.flatMap((chart) => chartValidationErrors(chart, song.beatmap_id).map((message) => `r${chart.revision_number}: ${message}`));
  const validation = metadataValidation(song, charts);
  return (
    <main style={pageStyle}>
      <Link href="/songs/">← Biblioteca</Link>
      <header style={{ margin: "22px 0" }}><p style={{ color: "#a6b1c2", letterSpacing: 2 }}>DETALHE DA FAIXA · REVISÃO {song.revision}</p><h1>{song.title}</h1><p>{song.artist} <span aria-label="dificuldade">· {song.difficulty}</span> <span>· {song.status}</span></p></header>
      {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(280px, .8fr)", gap: 18 }}>
        <section style={cardStyle}><h2>Metadados do jogo</h2><dl><dt>Game song ID</dt><dd>{song.game_song_id ?? "Não atribuído"}</dd><dt>Beatmap ID</dt><dd>{song.beatmap_id ?? "Não atribuído"}</dd><dt>BPM / compasso</dt><dd>{song.bpm ?? "—"} / {song.time_signature ?? "—"}</dd><dt>Origem</dt><dd>{song.source}</dd><dt>Variante</dt><dd>{song.variant_label ?? "—"}</dd></dl>
          <form onSubmit={saveMetadata} style={{ display: "grid", gap: 12 }}><h3>Editar metadados</h3><label>Título <input name="title" required maxLength={200} defaultValue={song.title} disabled={busy || song.status === "archived"} /></label><label>Artista <input name="artist" required maxLength={200} defaultValue={song.artist} disabled={busy || song.status === "archived"} /></label><label>Dificuldade <select name="difficulty" defaultValue={song.difficulty} disabled={busy || song.status === "archived"}>{DIFFICULTIES.map((difficulty) => <option key={difficulty} value={difficulty}>{difficulty}</option>)}</select></label><button disabled={busy || song.status === "archived"}>Salvar metadados</button></form>
        </section>
        <section style={cardStyle}><h2>Mídia</h2><div aria-label="Capa da música" style={{ aspectRatio: "1", display: "grid", placeItems: "center", background: "#202b39", borderRadius: 12, color: "#a6b1c2" }}>Capa não vinculada nesta consulta</div><p><strong>Áudio</strong> · status não exposto pela API de leitura</p><p style={{ color: "#a6b1c2" }}>Os vínculos de assets não são retornados pelo endpoint de detalhe.</p></section>
      </div>
      <section style={{ ...cardStyle, marginTop: 18 }}><h2>Chart preview</h2>{charts.length ? charts.map((chart) => <article key={chart.id} style={{ marginBottom: 20 }}><h3>Revisão de chart {chart.revision_number} · {chart.note_count} notas</h3><ChartPreview firstBeat={chart.first_beat} lastBeat={chart.last_beat} /><p>Beatmap {chart.beatmap_id} · SHA-256 disponível no resumo · formato v{chart.schema_version}</p></article>) : <p>Nenhuma revisão de chart cadastrada.</p>}<p>Esta visualização não confirma reprodução no cliente nativo.</p></section>
      <section style={cardStyle}><h2>Validação do formato</h2>{validation.length + chartErrors.length ? <ul>{[...validation, ...chartErrors].map((message) => <li key={message}>{message}</li>)}</ul> : <p>Sem inconsistências detectadas nos campos disponíveis. Reprodução nativa não verificada.</p>}</section>
      <section style={{ ...cardStyle, display: "flex", gap: 12, marginTop: 18 }}><h2>Ações</h2>{song.status === "archived" ? <button disabled={busy} onClick={() => void transition("restore")}>Restaurar</button> : <button disabled={busy} onClick={() => void transition("archive")}>Arquivar</button>}{song.status === "draft" && <button disabled={busy} onClick={() => void transition("delete")}>Excluir rascunho</button>}</section>
    </main>
  );
}

const pageStyle: React.CSSProperties = { maxWidth: 1120, margin: "0 auto", padding: 32, minHeight: "100vh", background: "#10151d", color: "#e9edf3", fontFamily: "system-ui" };
const cardStyle: React.CSSProperties = { padding: 22, border: "1px solid #293442", borderRadius: 16, background: "#151d28", marginBottom: 18 };

function metadataValidation(song: Song, charts: ChartSummary[]): string[] {
  const errors: string[] = [];
  if (song.game_song_id === null) errors.push("Game song ID não atribuído.");
  if (song.beatmap_id === null) errors.push("Beatmap ID não atribuído.");
  if (song.bpm === null) errors.push("BPM não definido.");
  if (charts.length === 0) errors.push("Nenhuma revisão de chart disponível.");
  return errors;
}

function confirmation(action: "archive" | "restore" | "delete", title: string): string {
  const labels = { archive: "Arquivar", restore: "Restaurar", delete: "Excluir permanentemente" };
  return `${labels[action]} “${title}”? Essa ação será registrada.`;
}

async function handleFailure(failure: unknown, refresh: () => Promise<void>, setError: (message: string) => void): Promise<void> {
  if (failure instanceof Error && "currentRevision" in failure) {
    setError("A revisão mudou em outra sessão. Os dados atuais foram recarregados; revise antes de salvar novamente.");
    await refresh();
    return;
  }
  setError(failure instanceof Error ? failure.message : "A ação não foi concluída.");
}
