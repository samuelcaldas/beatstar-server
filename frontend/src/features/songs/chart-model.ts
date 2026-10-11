export interface ChartNote {
  beat_offset: number;
  lane: 1 | 2 | 3;
  interaction: "tap" | "drag";
}

export interface ChartSummary {
  schema_version: number;
  beatmap_id: number;
  unsupported_count: number;
  note_count: number;
}

export interface MarkerPosition {
  x: number;
  y: number;
  kind: ChartNote["interaction"];
}

/** Maps a game beat and lane to normalized chart coordinates. */
export function markerPosition(note: ChartNote, firstBeat: number, lastBeat: number): MarkerPosition {
  const beatRange = lastBeat - firstBeat;
  const x = beatRange === 0 ? 0.5 : (note.beat_offset - firstBeat) / beatRange;
  return { x, y: (note.lane - 0.5) / 3, kind: note.interaction };
}

/** Lists structural issues exposed by the chart summary; it cannot certify native playback. */
export function chartValidationErrors(chart: ChartSummary, expectedBeatmapId: number | null): string[] {
  const errors: string[] = [];
  if (chart.schema_version !== 1) errors.push(`Versão de formato não reconhecida: ${chart.schema_version}.`);
  if (expectedBeatmapId !== null && chart.beatmap_id !== expectedBeatmapId) {
    errors.push(`O chart pertence ao beatmap ${chart.beatmap_id}, mas a música usa ${expectedBeatmapId}.`);
  }
  if (chart.unsupported_count > 0) errors.push(`${chart.unsupported_count} interações não são exibidas no resumo da API.`);
  if (chart.note_count === 0) errors.push("O chart não contém notas resumidas.");
  return errors;
}

/** Adds the current revision to a metadata change for optimistic concurrency. */
export function withExpectedRevision<T extends Record<string, unknown>>(changes: T, revision: number): T & { expected_revision: number } {
  return { ...changes, expected_revision: revision };
}
