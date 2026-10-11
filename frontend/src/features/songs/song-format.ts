/**
 * Song format rules shared by the administration UI. They mirror the server's limits so that
 * invalid input is reported next to the field, before a request is sent.
 */

export const DIFFICULTIES = ["tutorial", "easy", "normal", "hard", "expert"] as const;
export type Difficulty = (typeof DIFFICULTIES)[number];

export const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  tutorial: "Tutorial",
  easy: "Fácil",
  normal: "Normal",
  hard: "Difícil",
  expert: "Expert",
};

export const LANES = [1, 2, 3] as const;
export const MAXIMUM_NOTES = 5000;
export const MAXIMUM_BEAT = 100000;

export interface ChartNote {
  beat_offset: number;
  lane: number;
}

export interface NoteParseResult {
  notes: ChartNote[];
  errors: string[];
}

/**
 * Parses one note per line as "beat lane" (for example "8 1" or "16.5, 3").
 * Blank lines and lines starting with # are ignored. Every problem is reported with its line
 * number; notes are returned only when the whole text is valid, so a partial chart is never sent.
 */
export function parseNoteLines(text: string): NoteParseResult {
  const notes: ChartNote[] = [];
  const errors: string[] = [];
  const seen = new Set<string>();
  text.split(/\r?\n/).forEach((rawLine, index) => {
    const line = rawLine.trim();
    if (line === "" || line.startsWith("#")) return;
    const parsed = parseNoteLine(line);
    if (parsed === null) {
      errors.push(`Linha ${index + 1}: use "batida pista", por exemplo "8 1"`);
      return;
    }
    const key = `${parsed.beat_offset}:${parsed.lane}`;
    if (seen.has(key)) {
      errors.push(`Linha ${index + 1}: a nota ${parsed.beat_offset} na pista ${parsed.lane} já existe`);
      return;
    }
    seen.add(key);
    notes.push(parsed);
  });
  if (notes.length === 0 && errors.length === 0) errors.push("Informe ao menos uma nota");
  if (notes.length > MAXIMUM_NOTES) errors.push(`Um chart aceita no máximo ${MAXIMUM_NOTES} notas`);
  return errors.length > 0 ? { notes: [], errors } : { notes, errors };
}

function parseNoteLine(line: string): ChartNote | null {
  const tokens = line.split(/[\s,;]+/).filter((token) => token !== "");
  if (tokens.length !== 2) return null;
  const beat = Number(tokens[0]);
  const lane = Number(tokens[1]);
  if (!Number.isFinite(beat) || beat < 0 || beat > MAXIMUM_BEAT) return null;
  if (!(LANES as readonly number[]).includes(lane)) return null;
  return { beat_offset: beat, lane };
}

/** Formats tempo and meter as shown in the library, for example "98 BPM · 4/4". */
export function formatTempo(bpm: number | null, timeSignature: number | null): string {
  if (bpm === null) return "Sem andamento definido";
  const meter = timeSignature === null ? "" : ` · ${timeSignature}/4`;
  return `${Number.isInteger(bpm) ? bpm : bpm.toFixed(1)} BPM${meter}`;
}

/** Reads an optional numeric form field; blank means "not provided", anything else must be a number. */
export function parseOptionalNumber(raw: string): number | null | "invalid" {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed.replace(",", "."));
  return Number.isFinite(value) ? value : "invalid";
}

/** Returns the label for a difficulty value, falling back to the stored value for unknown ones. */
export function difficultyLabel(difficulty: string): string {
  return (DIFFICULTIES as readonly string[]).includes(difficulty)
    ? DIFFICULTY_LABELS[difficulty as Difficulty]
    : difficulty;
}
