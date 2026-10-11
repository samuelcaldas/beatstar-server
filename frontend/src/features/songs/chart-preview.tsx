import { markerPosition, type ChartNote } from "./chart-model";

interface ChartPreviewProps {
  notes?: ChartNote[];
  firstBeat: number | null;
  lastBeat: number | null;
}

/** Draws three Beatstar lanes without inventing note positions missing from the API response. */
export function ChartPreview({ notes = [], firstBeat, lastBeat }: ChartPreviewProps) {
  const start = firstBeat ?? 0;
  const end = lastBeat ?? 1;
  return (
    <figure aria-label="Prévia do chart em três lanes" style={{ margin: 0 }}>
      <svg role="img" aria-label="Três lanes com offsets de beat" viewBox="0 0 720 220" width="100%" style={{ background: "#151d28", borderRadius: 12 }}>
        {[1, 2, 3].map((lane) => <g key={lane}><line x1="64" x2="690" y1={lane * 55} y2={lane * 55} stroke="#394656" strokeWidth="1" /><text x="18" y={lane * 55 + 5} fill="#c7d2e0" fontSize="14">Lane {lane}</text></g>)}
        {notes.map((note, index) => {
          const position = markerPosition(note, start, end);
          const x = 64 + position.x * 626;
          const y = 27.5 + position.y * 165;
          return position.kind === "drag"
            ? <rect key={`${note.beat_offset}-${note.lane}-${index}`} x={x - 7} y={y - 7} width="14" height="14" transform={`rotate(45 ${x} ${y})`} fill="#68d5c3"><title>{`Drag · beat ${note.beat_offset} · lane ${note.lane}`}</title></rect>
            : <circle key={`${note.beat_offset}-${note.lane}-${index}`} cx={x} cy={y} r="7" fill="#9baeff"><title>{`Tap · beat ${note.beat_offset} · lane ${note.lane}`}</title></circle>;
        })}
        <text x="64" y="210" fill="#a6b1c2" fontSize="12">Beat {start}</text><text x="630" y="210" fill="#a6b1c2" fontSize="12">Beat {end}</text>
      </svg>
      <figcaption style={{ color: "#a6b1c2", marginTop: 8 }}>{notes.length ? "Tap: círculo · Drag: losango" : "A API fornece apenas o resumo do chart, sem posições para desenhar notas."}</figcaption>
    </figure>
  );
}
