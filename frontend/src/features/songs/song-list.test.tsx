// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SongList } from "./song-list";
import type { SongPage } from "./song-types";

const page: SongPage = {
  items: [{ id: "song-1", title: "Aurora", artist: "Lia", difficulty: "hard", game_song_id: null, beatmap_id: null, bpm: null, time_signature: null, variant_label: null, source: "manual", status: "draft", revision: 2, created_at: 0, updated_at: 0 }],
  total: 21,
  page: 1,
  page_size: 20,
};

describe("SongList", () => {
  it("renders songs and provides filter and pagination controls", async () => {
    const loadSongs = vi.fn().mockResolvedValue(page);
    render(<SongList loadSongs={loadSongs} />);
    expect(await screen.findByText("Aurora")).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "Filtrar por status" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Próxima página" }));
    expect(await screen.findByText("Página 2 de 2")).toBeTruthy();
  });
});
