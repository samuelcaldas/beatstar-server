"""Chart documents stored in chart_revisions: the Raksha bytes the game reads, plus a summary.

The raw Raksha bytes are the payload the game loads; the JSON wrapper keeps validated interaction
summaries for the administration UI. Tap and drag notes are decoded, validated, and represented;
other known interaction kinds remain in the raw bytes and are explicitly counted as unsupported.
"""

import base64
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass

from server.music.raksha import (
    BeatmapInteractionsTemplate,
    DragInteractionData,
    FlickDirection,
    InteractionData,
    InteractionPoint,
    InteractionType,
    TapInteractionData,
    decode_beatmap_interactions,
    encode_beatmap_interactions,
)

DOCUMENT_FORMAT = "beatstar-raksha-chart"
SCHEMA_VERSION = 1
LANES = (1, 2, 3)
MAXIMUM_BEAT = 100_000.0
MAXIMUM_NOTES = 5_000


@dataclass(frozen=True)
class ChartPoint:
    """A validated point in a tap or drag interaction."""

    beat_offset: float
    lane: int

    def __post_init__(self) -> None:
        """Rejects invalid beat positions and lane numbers."""
        _validate_point(self.beat_offset, self.lane)


@dataclass(frozen=True)
class ChartNote:
    """A tap or drag interaction represented in beat and lane coordinates."""

    beat_offset: float
    lane: int
    interaction_type: str = "TAP"
    drag_points: tuple[ChartPoint, ...] = ()
    flick: int = 0

    def __post_init__(self) -> None:
        """Validates the interaction kind, its points and flick direction."""
        _validate_point(self.beat_offset, self.lane)
        if self.interaction_type not in {"TAP", "DRAG"}:
            raise ValueError("Interaction type must be TAP or DRAG")
        if self.interaction_type == "DRAG" and len(self.drag_points) < 2:
            raise ValueError("Drag interactions require at least two points")
        if self.interaction_type == "DRAG" and self.drag_points[0] != ChartPoint(self.beat_offset, self.lane):
            raise ValueError("Drag start point must match its interaction beat and lane")
        if self.interaction_type == "TAP" and self.drag_points:
            raise ValueError("Tap interactions cannot contain drag points")
        _validate_flick(self.flick)
        _validate_sorted_points(self.drag_points)


def encode_notes(beatmap_id: int, id_label: str, notes: list[ChartNote]) -> bytes:
    """Encodes tap and drag notes as sorted Raksha interactions.

    Raises:
        ValueError: when notes are empty, duplicated, or exceed the supported count.
    """
    if not 1 <= len(notes) <= MAXIMUM_NOTES:
        raise ValueError("A chart needs between 1 and 5000 interactions")
    positions = {(note.beat_offset, note.lane) for note in notes}
    if len(positions) != len(notes):
        raise ValueError("Two interactions cannot share the same start beat and lane")
    interactions = [_interaction(note) for note in sorted(notes, key=lambda note: (note.beat_offset, note.lane))]
    template = BeatmapInteractionsTemplate(id=beatmap_id, id_label=id_label, interactions=interactions)
    return encode_beatmap_interactions(template)


def document_from_raw(raw: bytes) -> dict:
    """Wraps existing Raksha bytes with their summary; the bytes are decoded to validate them.

    Raises:
        ValueError: when the bytes are not a decodable Raksha chart.
    """
    try:
        template = decode_beatmap_interactions(raw)
    except (ValueError, TypeError, IndexError) as failure:
        raise ValueError("Bytes are not a decodable Raksha chart") from failure
    notes, unsupported = _tap_notes(template.interactions)
    interactions = _interaction_summaries(template.interactions)
    return _document(template.id, template.id_label, notes, unsupported, raw, interactions)


def document_from_notes(beatmap_id: int, id_label: str, notes: list[ChartNote]) -> dict:
    """Builds a chart document from notes authored in the administration UI."""
    raw = encode_notes(beatmap_id, id_label, notes)
    template = decode_beatmap_interactions(raw)
    return _document(beatmap_id, id_label, notes, 0, raw, _interaction_summaries(template.interactions))


def serialize(document: dict) -> str:
    """Returns the canonical JSON text stored in chart_revisions.document."""
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def raw_bytes(document: dict) -> bytes:
    """Returns the Raksha bytes embedded in a document."""
    return base64.b64decode(document["raw_base64"])


def summarize(stored: str) -> dict:
    """Returns the summary fields of a stored document without the raw payload."""
    document = json.loads(stored)
    return {key: value for key, value in document.items() if key != "raw_base64"}


def _interaction(note: ChartNote) -> InteractionData:
    """Builds one Raksha interaction from a validated tap or drag note."""
    interaction_type = InteractionType[note.interaction_type]
    if interaction_type == InteractionType.DRAG:
        points = [_raksha_point(point) for point in note.drag_points]
        return InteractionData(
            interaction_type=interaction_type,
            track=note.lane,
            drag_data=DragInteractionData(points=points, flick=FlickDirection(note.flick)),
        )
    point = InteractionPoint(beat_offset=note.beat_offset, lane=note.lane)
    return InteractionData(
        interaction_type=interaction_type,
        track=note.lane,
        tap_data=TapInteractionData(point=point, flick=FlickDirection(note.flick)),
    )


def _raksha_point(point: ChartPoint) -> InteractionPoint:
    """Converts a validated domain point to the Raksha model."""
    return InteractionPoint(beat_offset=point.beat_offset, lane=point.lane)


def _tap_notes(interactions: list[InteractionData]) -> tuple[list[ChartNote], int]:
    """Returns taps for compatibility summaries and counts known non-tap interaction types."""
    notes: list[ChartNote] = []
    unsupported = 0
    for interaction in interactions:
        if interaction.interaction_type == InteractionType.DRAG:
            continue
        if interaction.interaction_type != InteractionType.TAP:
            unsupported += 1
            continue
        if interaction.tap_data is None or interaction.drag_data is not None:
            raise ValueError("Tap interaction must contain tap data only")
        point = interaction.tap_data.point
        _validate_point(point.beat_offset, point.lane)
        _validate_point(interaction.tap_data.point.beat_offset, interaction.track)
        _validate_flick(int(interaction.tap_data.flick))
        notes.append(ChartNote(beat_offset=point.beat_offset, lane=point.lane, flick=int(interaction.tap_data.flick)))
    return notes, unsupported


def _interaction_summaries(interactions: list[InteractionData]) -> list[dict]:
    """Validates decoded interactions and returns stable, sorted JSON-friendly details."""
    summaries = [_summarize_interaction(interaction) for interaction in interactions]
    return sorted(summaries, key=lambda item: (item["points"][0]["beat_offset"] if item["points"] else -1, item["track"]))


def _summarize_interaction(interaction: InteractionData) -> dict:
    """Validates one decoded Raksha interaction and exposes its points and flick direction."""
    try:
        interaction_type = InteractionType(interaction.interaction_type)
    except ValueError as error:
        raise ValueError("Chart contains an unknown interaction type") from error
    if interaction.track not in LANES:
        raise ValueError("Interaction track must be lane 1, 2 or 3")
    if interaction_type == InteractionType.TAP:
        if interaction.tap_data is None or interaction.drag_data is not None:
            raise ValueError("Tap interaction must contain tap data only")
        points = [interaction.tap_data.point]
        flick = int(interaction.tap_data.flick)
    elif interaction_type == InteractionType.DRAG:
        if interaction.drag_data is None or interaction.tap_data is not None:
            raise ValueError("Drag interaction must contain drag data only")
        if len(interaction.drag_data.points) < 2:
            raise ValueError("Drag interactions require at least two points")
        points = interaction.drag_data.points
        flick = int(interaction.drag_data.flick)
    else:
        points = []
        flick = 0
    _validate_flick(flick)
    for point in points:
        _validate_point(point.beat_offset, point.lane)
    point_data = [{"beat_offset": point.beat_offset, "lane": point.lane} for point in points]
    _validate_sorted_offsets([point["beat_offset"] for point in point_data])
    return {"type": interaction_type.name, "track": interaction.track, "flick": flick, "points": point_data}


def _validate_point(beat_offset: float, lane: int) -> None:
    """Rejects a non-finite/out-of-range beat or lane outside the game format."""
    if not math.isfinite(beat_offset) or not 0 <= beat_offset <= MAXIMUM_BEAT:
        raise ValueError("Note beat must be a finite value between 0 and 100000")
    if lane not in LANES:
        raise ValueError("Note lane must be 1, 2 or 3")


def _validate_flick(flick: int) -> None:
    """Rejects a flick value absent from the Raksha enumeration."""
    try:
        FlickDirection(flick)
    except ValueError as error:
        raise ValueError("Interaction has an unknown flick direction") from error


def _validate_sorted_points(points: tuple[ChartPoint, ...]) -> None:
    """Rejects drag paths that move backwards in beat time."""
    _validate_sorted_offsets([point.beat_offset for point in points])


def _validate_sorted_offsets(offsets: list[float]) -> None:
    """Rejects offsets that are not in non-decreasing beat order."""
    if offsets != sorted(offsets):
        raise ValueError("Interaction beat offsets must be sorted")


def _document(
    beatmap_id: int, id_label: str, notes: list[ChartNote], unsupported: int, raw: bytes,
    interactions: list[dict],
) -> dict:
    """Assembles the versioned JSON wrapper with note details and raw Raksha bytes."""
    points = [point for item in interactions for point in item["points"]]
    lanes = Counter(item["points"][0]["lane"] for item in interactions if item["points"])
    beats = [point["beat_offset"] for point in points]
    return {
        "format": DOCUMENT_FORMAT,
        "schema_version": SCHEMA_VERSION,
        "beatmap_id": beatmap_id,
        "id_label": id_label,
        "note_count": len(interactions),
        "unsupported_count": unsupported,
        "lanes": {str(lane): lanes.get(lane, 0) for lane in LANES},
        "first_beat": min(beats) if beats else None,
        "last_beat": max(beats) if beats else None,
        "interactions": interactions,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_base64": base64.b64encode(raw).decode("ascii"),
    }
