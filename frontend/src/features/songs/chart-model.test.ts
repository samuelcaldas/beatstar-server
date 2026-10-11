import { describe, expect, it } from "vitest";
import { chartValidationErrors, markerPosition, withExpectedRevision, type ChartNote, type ChartSummary } from "./chart-model";

describe("chart preview model", () => {
  it("maps beat offsets to a three-lane preview", () => {
    expect(markerPosition({ beat_offset: 4, lane: 2, interaction: "tap" }, 0, 8)).toEqual({ x: 0.5, y: 0.5, kind: "tap" });
  });

  it("preserves drag marker identity", () => {
    const note: ChartNote = { beat_offset: 2, lane: 3, interaction: "drag" };
    expect(markerPosition(note, 0, 4).kind).toBe("drag");
  });

  it("reports unsupported interactions without claiming playback validity", () => {
    const chart: ChartSummary = { schema_version: 1, beatmap_id: 12, unsupported_count: 2, note_count: 5 };
    expect(chartValidationErrors(chart, 12)).toContain("2 interações não são exibidas no resumo da API.");
  });

  it("reports a chart bound to a different beatmap", () => {
    const chart: ChartSummary = { schema_version: 1, beatmap_id: 3, unsupported_count: 0, note_count: 1 };
    expect(chartValidationErrors(chart, 12)).toContain("O chart pertence ao beatmap 3, mas a música usa 12.");
  });

  it("binds metadata edits to the displayed revision", () => {
    expect(withExpectedRevision({ title: "Aurora" }, 7)).toEqual({ title: "Aurora", expected_revision: 7 });
  });
});
