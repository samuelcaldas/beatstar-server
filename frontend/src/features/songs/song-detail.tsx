"use client";

import { useEffect, useState, type FormEvent } from "react";
import { describeFailure } from "./describe-failure";
import { difficultyLabel, formatTempo, parseNoteLines, parseOptionalNumber } from "./song-format";
import { assetContentUrl, type AssetRecord, type ChartRecord, type SongLibrary, type SongRecord } from "./songs-api";

interface SongDetailProps {
  library: SongLibrary;
  song: SongRecord;
  onChanged: (song: SongRecord) => void;
}

/** Shows one song's game identity, charts and artwork, and the actions the server allows for it. */
export function SongDetail({ library, song, onChanged }: SongDetailProps) {
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function runAction(action: () => Promise<SongRecord>) {
    setPending(true);
    setMessage(null);
    try {
      onChanged(await action());
    } catch (failure) {
      setMessage(describeFailure(failure));
    } finally {
      setPending(false);
    }
  }

  return (
    <article aria-label={`Detalhes de ${song.title}`}>
      <h2>{song.title}</h2>
      <p>
        {song.artist} · {difficultyLabel(song.difficulty)} · {formatTempo(song.bpm, song.time_signature)} ·
        Revisão {song.revision} · {song.source} · {song.status}
      </p>
      <p>ID da música: {song.game_song_id ?? "não atribuído"} · Beatmap: {song.beatmap_id ?? "não atribuído"} · Variante: {song.variant_label ?? "—"}</p>
      {message !== null && <p role="alert">{message}</p>}
      <div>
        {song.status === "archived" ? (
          <button type="button" disabled={pending} onClick={() => runAction(() => library.restore(song.id, song.revision))}>
            Restaurar para rascunho
          </button>
        ) : (
          <button type="button" disabled={pending} onClick={() => runAction(() => library.archive(song.id, song.revision))}>
            Arquivar
          </button>
        )}
      </div>
      {song.status !== "archived" && <GameFieldsForm library={library} song={song} onChanged={onChanged} />}
      <ArtworkPanel library={library} song={song} />
      <ChartPanel library={library} song={song} />
    </article>
  );
}

function GameFieldsForm({ library, song, onChanged }: SongDetailProps) {
  const [bpm, setBpm] = useState(song.bpm === null ? "" : String(song.bpm));
  const [timeSignature, setTimeSignature] = useState(song.time_signature === null ? "" : String(song.time_signature));
  const [variantLabel, setVariantLabel] = useState(song.variant_label ?? "");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedBpm = parseOptionalNumber(bpm);
    const parsedMeter = parseOptionalNumber(timeSignature);
    if (parsedBpm === "invalid" || parsedMeter === "invalid" || parsedBpm === null) {
      setMessage("Informe o BPM como número");
      return;
    }
    try {
      onChanged(await library.updateGameFields(song.id, {
        bpm: parsedBpm,
        time_signature: parsedMeter === null ? undefined : parsedMeter,
        variant_label: variantLabel.trim() || undefined,
        expected_revision: song.revision,
      }));
      setMessage("Alterações salvas");
    } catch (failure) {
      setMessage(describeFailure(failure));
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Identidade no jogo">
      <h3>Identidade no jogo</h3>
      <label>BPM <input inputMode="decimal" value={bpm} onChange={(event) => setBpm(event.target.value)} /></label>
      <label>Compasso <input inputMode="numeric" value={timeSignature} onChange={(event) => setTimeSignature(event.target.value)} /></label>
      <label>Variante <input value={variantLabel} onChange={(event) => setVariantLabel(event.target.value)} maxLength={64} /></label>
      <button type="submit">Salvar identidade</button>
      {message !== null && <p role="status">{message}</p>}
    </form>
  );
}

function ArtworkPanel({ library, song }: { library: SongLibrary; song: SongRecord }) {
  const [artwork, setArtwork] = useState<AssetRecord[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    library.assets(song.id)
      .then((assets) => setArtwork(assets.filter((asset) => asset.kind === "artwork")))
      .catch((failure: unknown) => setMessage(describeFailure(failure)));
  }, [library, song.id, version]);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await library.uploadArtwork(song.id, file, file.type);
      setMessage("Capa enviada");
      setVersion((current) => current + 1);
    } catch (failure) {
      setMessage(describeFailure(failure));
    }
  }

  return (
    <section aria-label="Capa">
      <h3>Capa</h3>
      {artwork.length === 0 && <p>Nenhuma capa enviada.</p>}
      {artwork.map((asset) => (
        <figure key={asset.id}>
          <img src={assetContentUrl(asset.id)} alt={`Capa de ${song.title}`} width={160} height={160} />
          <figcaption>{asset.width}×{asset.height} · {asset.content_type} · {asset.byte_size} bytes</figcaption>
        </figure>
      ))}
      {song.status !== "archived" && (
        <label>
          Enviar capa (PNG ou JPEG)
          <input type="file" accept="image/png,image/jpeg" onChange={handleFile} />
        </label>
      )}
      {message !== null && <p role="status">{message}</p>}
    </section>
  );
}

function ChartPanel({ library, song }: { library: SongLibrary; song: SongRecord }) {
  const [charts, setCharts] = useState<ChartRecord[]>([]);
  const [notesText, setNotesText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const parsed = parseNoteLines(notesText);
  const canSubmit = parsed.errors.length === 0 && song.beatmap_id !== null && song.status !== "archived";

  useEffect(() => {
    library.charts(song.id)
      .then(setCharts)
      .catch((failure: unknown) => setMessage(describeFailure(failure)));
  }, [library, song.id, version]);

  async function handleCreate() {
    try {
      const chart = await library.createChart(song.id, parsed.notes);
      setMessage(`Revisão ${chart.revision_number} criada com ${chart.note_count} notas`);
      setNotesText("");
      setVersion((current) => current + 1);
    } catch (failure) {
      setMessage(describeFailure(failure));
    }
  }

  return (
    <section aria-label="Charts">
      <h3>Charts</h3>
      {song.beatmap_id === null && <p>Atribua um ID de beatmap antes de criar charts.</p>}
      <table>
        <thead>
          <tr><th>Revisão</th><th>Notas</th><th>Pista 1</th><th>Pista 2</th><th>Pista 3</th><th>Primeira batida</th><th>Última batida</th><th>SHA-256</th></tr>
        </thead>
        <tbody>
          {charts.map((chart) => (
            <tr key={chart.id}>
              <td>{chart.revision_number}</td>
              <td>{chart.note_count}</td>
              <td>{chart.lanes["1"] ?? 0}</td>
              <td>{chart.lanes["2"] ?? 0}</td>
              <td>{chart.lanes["3"] ?? 0}</td>
              <td>{chart.first_beat ?? "—"}</td>
              <td>{chart.last_beat ?? "—"}</td>
              <td><code>{chart.raw_sha256.slice(0, 12)}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
      {song.beatmap_id !== null && song.status !== "archived" && (
        <div>
          <label>
            Notas (uma por linha: batida pista)
            <textarea rows={8} value={notesText} onChange={(event) => setNotesText(event.target.value)} />
          </label>
          {notesText.trim() !== "" && parsed.errors.length > 0 && (
            <ul role="alert">{parsed.errors.map((error) => <li key={error}>{error}</li>)}</ul>
          )}
          {notesText.trim() !== "" && parsed.errors.length === 0 && <p>{parsed.notes.length} notas válidas</p>}
          <button type="button" disabled={!canSubmit} onClick={handleCreate}>Criar nova revisão do chart</button>
        </div>
      )}
      {message !== null && <p role="status">{message}</p>}
    </section>
  );
}
