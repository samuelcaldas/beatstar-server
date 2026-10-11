import { describe, expect, it } from "vitest";
import {
  difficultyLabel,
  formatTempo,
  parseNoteLines,
  parseOptionalNumber,
} from "./song-format";

describe("parseNoteLines", () => {
  it("reads one beat and lane per line and skips blanks and comments", () => {
    const result = parseNoteLines("# intro\n\n8 1\n16.5, 3\n");

    expect(result.errors).toEqual([]);
    expect(result.notes).toEqual([
      { beat_offset: 8, lane: 1 },
      { beat_offset: 16.5, lane: 3 },
    ]);
  });

  it("names the line that breaks the lane rule", () => {
    const result = parseNoteLines("8 1\n9 4");

    expect(result.notes).toEqual([]);
    expect(result.errors).toEqual(['Linha 2: use "batida pista", por exemplo "8 1"']);
  });

  it("rejects duplicate beat and lane pairs instead of doubling the note", () => {
    const result = parseNoteLines("8 1\n8 1");

    expect(result.errors[0]).toContain("Linha 2");
    expect(result.errors[0]).toContain("já existe");
  });

  it("refuses an empty chart", () => {
    expect(parseNoteLines("  \n# só comentário").errors).toEqual(["Informe ao menos uma nota"]);
  });

  it("refuses negative beats and lanes outside 1 to 3", () => {
    expect(parseNoteLines("-1 1").errors).toHaveLength(1);
    expect(parseNoteLines("0 0").errors).toHaveLength(1);
  });
});

describe("formatTempo", () => {
  it("shows tempo and meter, or says the tempo is unset", () => {
    expect(formatTempo(98, 4)).toBe("98 BPM · 4/4");
    expect(formatTempo(98.5, null)).toBe("98.5 BPM");
    expect(formatTempo(null, null)).toBe("Sem andamento definido");
  });
});

describe("parseOptionalNumber", () => {
  it("treats blank as absent and accepts a decimal comma", () => {
    expect(parseOptionalNumber("   ")).toBeNull();
    expect(parseOptionalNumber("98,5")).toBe(98.5);
    expect(parseOptionalNumber("abc")).toBe("invalid");
  });
});

describe("difficultyLabel", () => {
  it("labels known difficulties in Portuguese and keeps unknown values visible", () => {
    expect(difficultyLabel("hard")).toBe("Difícil");
    expect(difficultyLabel("legend")).toBe("legend");
  });
});
