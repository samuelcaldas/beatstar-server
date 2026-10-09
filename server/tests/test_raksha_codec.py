"""Unit tests for Raksha Protobuf wire codec and beatmap serialization."""

from __future__ import annotations

from pathlib import Path
import pytest

from server.music.raksha import (
    BeatmapInteractionsTemplate,
    InteractionData,
    InteractionPoint,
    InteractionType,
    ProtoReader,
    ProtoWriter,
    TapInteractionData,
    decode_beatmap_interactions,
    encode_beatmap_interactions,
)
from server.music.reference_fixture import REFERENCE_SONG


def test_proto_wire_primitives_roundtrip():
    """Validates varint, float, string and length-delimited wire primitives."""
    writer = ProtoWriter()
    writer.write_varint_field(1, 42)
    writer.write_varint_field(2, 100000)
    writer.write_float_field(3, 123.456)
    writer.write_string_field(4, "Hello SpaceApe")
    writer.write_bytes_field(5, b"\x01\x02\x03\x04")

    raw = writer.to_bytes()
    reader = ProtoReader(raw)

    t1, w1 = reader.read_tag()
    assert t1 == 1 and reader.read_varint() == 42

    t2, w2 = reader.read_tag()
    assert t2 == 2 and reader.read_varint() == 100000

    t3, w3 = reader.read_tag()
    assert t3 == 3 and abs(reader.read_fixed32_float() - 123.456) < 1e-4

    t4, w4 = reader.read_tag()
    assert t4 == 4 and reader.read_string() == "Hello SpaceApe"

    t5, w5 = reader.read_tag()
    assert t5 == 5 and reader.read_bytes() == b"\x01\x02\x03\x04"


def test_reference_chart_660_exact_byte_roundtrip():
    """Validates bit-for-bit lossless roundtrip of reference chart 660.bytes."""
    chart_path = Path("data/extracted/660.chart.bytes")
    if not chart_path.exists():
        pytest.skip("data/extracted/660.chart.bytes not present in test environment")

    raw_original = chart_path.read_bytes()
    decoded = decode_beatmap_interactions(raw_original)

    assert decoded.id == REFERENCE_SONG.beatmap_id
    assert decoded.id_label == REFERENCE_SONG.chart_id_label
    assert len(decoded.interactions) == 97

    # Verify first note semantics
    first_note = decoded.interactions[0]
    assert first_note.interaction_type == InteractionType.TAP
    assert first_note.tap_data is not None
    assert first_note.tap_data.point.beat_offset == 8.0
    assert first_note.tap_data.point.lane == 1
    assert first_note.track == 1

    # Bit-for-bit roundtrip
    re_encoded = encode_beatmap_interactions(decoded)
    assert len(re_encoded) == len(raw_original)
    assert re_encoded == raw_original


def test_reference_chart_660_canonical_encoding_without_source_retention():
    """Validates schema coverage: fields are re-encoded from the model, not the retained source."""
    chart_path = Path("data/extracted/660.chart.bytes")
    if not chart_path.exists():
        pytest.skip("data/extracted/660.chart.bytes not present in test environment")

    raw_original = chart_path.read_bytes()
    detached = BeatmapInteractionsTemplate.model_validate(
        decode_beatmap_interactions(raw_original).model_dump()
    )

    assert encode_beatmap_interactions(detached) == raw_original


def test_beatmap_note_modification_and_reencoding():
    """Validates authoring operations: changing note timings, lanes and adding notes."""
    chart_path = Path("data/extracted/660.chart.bytes")
    if not chart_path.exists():
        pytest.skip("data/extracted/660.chart.bytes not present in test environment")

    decoded = decode_beatmap_interactions(chart_path.read_bytes())
    initial_count = len(decoded.interactions)

    # Modify existing note
    decoded.interactions[0].tap_data.point.beat_offset = 10.5
    decoded.interactions[0].tap_data.point.lane = 3
    decoded.interactions[0].track = 3

    # Add a new custom note
    new_note = InteractionData(
        interaction_type=InteractionType.TAP,
        track=2,
        tap_data=TapInteractionData(
            point=InteractionPoint(beat_offset=999.0, lane=2)
        ),
    )
    decoded.interactions.append(new_note)

    # Re-encode and verify deserialization
    re_encoded = encode_beatmap_interactions(decoded)
    re_decoded = decode_beatmap_interactions(re_encoded)

    assert len(re_decoded.interactions) == initial_count + 1
    assert re_decoded.interactions[0].tap_data.point.beat_offset == 10.5
    assert re_decoded.interactions[0].tap_data.point.lane == 3
    assert re_decoded.interactions[0].track == 3

    last_note = re_decoded.interactions[-1]
    assert last_note.tap_data.point.beat_offset == 999.0
    assert last_note.tap_data.point.lane == 2
    assert last_note.track == 2


def test_decode_all_extracted_apk_charts():
    """Verifies that all 60 extracted charts from APK decode cleanly without errors."""
    extracted_dir = Path("data/extracted")
    chart_files = list(extracted_dir.glob("*.chart.bytes"))
    if not chart_files:
        pytest.skip("No extracted chart files present in data/extracted")

    assert len(chart_files) == 60

    for chart_file in chart_files:
        raw = chart_file.read_bytes()
        chart = decode_beatmap_interactions(raw)
        assert chart.id > 0
        assert len(chart.id_label) > 0
        assert len(chart.interactions) > 0
        # Detached copy drops retained source bytes, so equality proves canonical coverage
        detached = BeatmapInteractionsTemplate.model_validate(chart.model_dump())
        assert encode_beatmap_interactions(detached) == raw
