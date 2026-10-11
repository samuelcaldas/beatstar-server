"""Reference song constructions for validating the administration flow end to end.

Each example is a deterministic set of tap and drag notes plus generated artwork. Beatmap identifiers come
from a reserved range (900000 and up) that the client never uses, so examples cannot collide with
imported charts. Audio is not generated: the server has no verified encoder for the client's bank
format, so an example song is a chart and cover only, and it is kept in draft state.
"""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageDraw

from server.music.chart_document import ChartNote, ChartPoint
from server.music.song_schemas import SongCreate

EXAMPLE_SOURCE = "example"
EXAMPLE_BEATMAP_BASE = 900_000
ARTWORK_SIZE = 512


@dataclass(frozen=True)
class ExampleSong:
    """Metadata, notes and artwork colours of one example construction."""

    beatmap_id: int
    metadata: SongCreate
    notes: tuple[ChartNote, ...]
    colours: tuple[tuple[int, int, int], tuple[int, int, int]]


def build_examples() -> tuple[ExampleSong, ...]:
    """Returns the examples in a fixed order; repeated calls return equal values."""
    return (
        _three_lane_pulse(),
        _staircase(),
    )


def artwork_png(example: ExampleSong) -> bytes:
    """Draws a square gradient with the lane count and tempo, as PNG bytes."""
    top, bottom = example.colours
    image = Image.new("RGB", (ARTWORK_SIZE, ARTWORK_SIZE), top)
    draw = ImageDraw.Draw(image)
    for row in range(ARTWORK_SIZE):
        ratio = row / (ARTWORK_SIZE - 1)
        colour = tuple(round(a + (b - a) * ratio) for a, b in zip(top, bottom, strict=True))
        draw.line([(0, row), (ARTWORK_SIZE, row)], fill=colour)
    for lane in (1, 2, 3):
        left = (lane - 1) * ARTWORK_SIZE // 3 + 24
        draw.rectangle([left, 180, left + ARTWORK_SIZE // 3 - 48, 332], outline=(255, 255, 255), width=6)
    draw.text((24, 24), example.metadata.title, fill=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _three_lane_pulse() -> ExampleSong:
    """64 notes, one per beat, cycling through the three lanes at 120 BPM."""
    taps = [ChartNote(beat_offset=float(beat), lane=beat % 3 + 1) for beat in range(4, 68)]
    taps.append(ChartNote(
        beat_offset=68.0, lane=1, interaction_type="DRAG",
        drag_points=(ChartPoint(68.0, 1), ChartPoint(70.0, 2), ChartPoint(72.0, 3)),
    ))
    notes = tuple(taps)
    return ExampleSong(
        beatmap_id=EXAMPLE_BEATMAP_BASE + 1,
        metadata=_metadata("Exemplo · Pulso em três pistas", "Teste de construção", "easy", 120.0, 1),
        notes=notes,
        colours=((30, 64, 175), (14, 116, 144)),
    )


def _staircase() -> ExampleSong:
    """Eight-note bars climbing 1-2-3-2 with off-beat notes, at 90 BPM."""
    pattern = (1, 2, 3, 2)
    notes = []
    for bar in range(8):
        for step in range(8):
            beat = 4 + bar * 4 + step * 0.5
            notes.append(ChartNote(beat_offset=beat, lane=pattern[step % 4]))
    notes.append(ChartNote(
        beat_offset=36.0, lane=2, interaction_type="DRAG",
        drag_points=(ChartPoint(36.0, 2), ChartPoint(38.0, 3)),
    ))
    return ExampleSong(
        beatmap_id=EXAMPLE_BEATMAP_BASE + 2,
        metadata=_metadata("Exemplo · Escada com contratempo", "Teste de construção", "normal", 90.0, 2),
        notes=tuple(notes),
        colours=((124, 45, 18), (234, 88, 12)),
    )


def _metadata(title: str, artist: str, difficulty: str, bpm: float, number: int) -> SongCreate:
    """Builds the song metadata for one example; the variant label names the example uniquely."""
    return SongCreate(
        title=title,
        artist=artist,
        difficulty=difficulty,
        beatmap_id=EXAMPLE_BEATMAP_BASE + number,
        bpm=bpm,
        time_signature=4,
        variant_label=f"EXAMPLE-{number:02d}",
    )
